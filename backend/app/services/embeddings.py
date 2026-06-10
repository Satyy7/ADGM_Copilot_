"""Gemini embeddings service for the ADGM Compliance Copilot.

Purpose
-------
Provides a single, reusable ``EmbeddingsService`` that wraps the
``google-genai`` SDK (v1+). All layers that need vectors — the knowledge-base
indexer (Phase 4), baseline retrieval (Phase 5), and future LangGraph nodes
(Phase 8+) — import from this module so embedding logic never duplicates.

Architecture Integration
------------------------
* Instantiated once per process via ``get_embeddings_service()``.
* Accepts an optional Redis client: when supplied, embeddings are cached for
  7 days to avoid redundant API calls (wired fully in Phase 16).
* ``EmbeddingTaskType`` distinguishes document indexing from query-time
  retrieval — Gemini returns higher-quality vectors when the task type matches
  the downstream use case.
* ``EMBEDDING_DIMENSION`` is the authoritative dimension constant imported by
  the Qdrant indexer when creating collections.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from enum import Enum
from typing import TYPE_CHECKING

from google import genai
from google.genai import types

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.source import KnowledgeChunk

if TYPE_CHECKING:
    import redis as redis_lib

logger = logging.getLogger(__name__)

# ── Module-level constants ─────────────────────────────────────────────────────

EMBEDDING_DIMENSION: int = 768
"""Output vector size for gemini-embedding-001.

Imported by the Qdrant indexer to configure collection vector params.
Change here if you switch to a different embedding model or dimension.
"""

EMBEDDING_BATCH_SIZE: int = 20
"""Maximum texts per single API call.

Keeps individual request latency low and leaves headroom against
per-minute quota limits.
"""

_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
_MAX_RETRIES: int = 5
_BASE_BACKOFF: float = 1.0  # seconds; doubles each retry + jitter
_INTER_BATCH_SLEEP: float = 1.5  # seconds between consecutive batch API calls


# ── Task type enum ─────────────────────────────────────────────────────────────

class EmbeddingTaskType(str, Enum):
    """Gemini task types that guide embedding quality for specific use cases."""

    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    """Use when embedding chunks for indexing into a vector store."""

    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    """Use when embedding a user question at query time."""

    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"


# ── Service ────────────────────────────────────────────────────────────────────

class EmbeddingsService:
    """Gemini embeddings with batching, exponential-backoff retry, and caching.

    Parameters
    ----------
    settings:
        Application settings. Defaults to the global ``get_settings()`` cache.
    redis_client:
        Optional connected Redis client for embedding caching. When ``None``
        every call hits the Gemini API (Phase 16 wires this in fully).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        redis_client: "redis_lib.Redis | None" = None,
    ) -> None:
        resolved = settings or get_settings()
        if resolved.gemini_api_key is None:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        self._client = genai.Client(api_key=resolved.gemini_api_key.get_secret_value())
        self._model = resolved.gemini_embedding_model
        self._redis = redis_client
        logger.info("EmbeddingsService ready — model=%s dim=%d", self._model, EMBEDDING_DIMENSION)

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed_text(
        self,
        text: str,
        task_type: EmbeddingTaskType = EmbeddingTaskType.RETRIEVAL_QUERY,
    ) -> list[float]:
        """Return the embedding vector for a single text string."""
        results = self.embed_batch([text], task_type=task_type)
        return results[0]

    def embed_batch(
        self,
        texts: list[str],
        task_type: EmbeddingTaskType = EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    ) -> list[list[float]]:
        """Embed a list of texts, using Redis cache when available.

        Texts are split into batches of ``EMBEDDING_BATCH_SIZE`` internally.
        Cache hits are resolved first; only uncached texts reach the API.
        """
        if not texts:
            return []

        vectors: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for idx, text in enumerate(texts):
            cached = self._cache_get(text, task_type)
            if cached is not None:
                vectors[idx] = cached
            else:
                uncached_indices.append(idx)
                uncached_texts.append(text)

        cache_hits = len(texts) - len(uncached_texts)
        if cache_hits:
            logger.debug("Embedding cache: %d hits, %d misses.", cache_hits, len(uncached_texts))

        if uncached_texts:
            logger.info(
                "Requesting %d embeddings from Gemini (task=%s).",
                len(uncached_texts),
                task_type.value,
            )
            fresh_vectors = self._embed_with_batching(uncached_texts, task_type)
            for pos, original_idx in enumerate(uncached_indices):
                vec = fresh_vectors[pos]
                vectors[original_idx] = vec
                self._cache_set(uncached_texts[pos], task_type, vec)

        return [v for v in vectors if v is not None]  # type: ignore[misc]

    def embed_chunks(
        self,
        chunks: list[KnowledgeChunk],
    ) -> list[tuple[KnowledgeChunk, list[float]]]:
        """Embed a list of ``KnowledgeChunk`` objects for Qdrant indexing."""
        if not chunks:
            return []
        texts = [chunk.text for chunk in chunks]
        vectors = self.embed_batch(texts, task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT)
        return list(zip(chunks, vectors))

    # ── Internal batching ──────────────────────────────────────────────────────

    def _embed_with_batching(
        self,
        texts: list[str],
        task_type: EmbeddingTaskType,
    ) -> list[list[float]]:
        """Split texts into API-safe batches and collect results."""
        results: list[list[float]] = []
        total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
        for batch_num, start in enumerate(range(0, len(texts), EMBEDDING_BATCH_SIZE), 1):
            batch = texts[start : start + EMBEDDING_BATCH_SIZE]
            logger.debug("Embedding batch %d/%d (%d texts).", batch_num, total_batches, len(batch))
            results.extend(self._embed_batch_with_retry(batch, task_type))
            if batch_num < total_batches:
                time.sleep(_INTER_BATCH_SLEEP)
        return results

    def _embed_batch_with_retry(
        self,
        texts: list[str],
        task_type: EmbeddingTaskType,
    ) -> list[list[float]]:
        """Call Gemini embed_content with exponential backoff on rate limits."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=task_type.value,
                        output_dimensionality=EMBEDDING_DIMENSION,
                    ),
                )
                return [list(e.values) for e in response.embeddings]
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                is_rate_limit = any(
                    t in exc_str for t in ("429", "quota", "rate limit", "resource exhausted")
                )
                if is_rate_limit:
                    backoff = _BASE_BACKOFF * (2**attempt) + random.uniform(0.0, 1.0)
                    logger.warning(
                        "Gemini rate limit (attempt %d/%d). Backing off %.1fs.",
                        attempt + 1, _MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error("Non-retryable embedding error: %s", exc)
                    raise

        raise RuntimeError(
            f"Gemini embedding failed after {_MAX_RETRIES} retries."
        ) from last_exc

    # ── Redis cache helpers ────────────────────────────────────────────────────

    def _cache_key(self, text: str, task_type: EmbeddingTaskType) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
        model_slug = self._model.replace("/", "-").replace(".", "_")
        return f"embed:{model_slug}:{task_type.value}:{digest}"

    def _cache_get(self, text: str, task_type: EmbeddingTaskType) -> list[float] | None:
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(self._cache_key(text, task_type))
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug("Redis cache get skipped: %s", exc)
            return None

    def _cache_set(self, text: str, task_type: EmbeddingTaskType, vector: list[float]) -> None:
        if self._redis is None:
            return
        try:
            self._redis.set(
                self._cache_key(text, task_type),
                json.dumps(vector),
                ex=_CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("Redis cache set skipped: %s", exc)


# ── Factory ────────────────────────────────────────────────────────────────────

def get_embeddings_service(
    settings: Settings | None = None,
    redis_client: "redis_lib.Redis | None" = None,
) -> EmbeddingsService:
    """Construct an ``EmbeddingsService``.

    Pass ``redis_client=get_redis_client()`` to enable embedding caching.
    """
    return EmbeddingsService(settings=settings, redis_client=redis_client)
