"""Caching wrapper for any Retriever-protocol object — Phase 16.

Architecture
------------
``CachedRetriever`` is a transparent decorator: it accepts exactly the same
``search(question, collections, top_k)`` signature as every other retriever and
returns the same ``list[RetrievedChunk]`` type.  It sits at the *outermost*
layer of the retrieval stack so a single cache hit short-circuits the entire
pipeline:

    CachedRetriever         ← Phase 16 (this file)
        → HyDERetriever     ← Phase 13
            → RerankedRetriever  ← Phase 7
                → HybridRetriever    ← Phase 6
                    → QdrantRetriever + BM25Retriever

Cache key
---------
SHA-256 of the normalised ``"question|sorted(collections)|top_k"`` string,
truncated to 24 hex characters.  Key prefix: ``retrieval:``.

TTL
---
30 minutes.  Short enough that freshly indexed documents appear quickly;
long enough to absorb burst traffic on repeated compliance questions.

Serialisation
-------------
``RetrievedChunk`` is a Pydantic model — ``.model_dump()`` produces a clean
dict and ``.model_validate()`` reconstructs it from that dict.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from backend.app.schemas.rag import RetrievedChunk

if TYPE_CHECKING:
    import redis as redis_lib

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS: int = 30 * 60   # 30 minutes
_KEY_PREFIX = "retrieval"


class CachedRetriever:
    """Transparent retrieval cache backed by Redis.

    Parameters
    ----------
    base:
        The retriever to delegate to on cache misses.
    redis_client:
        Connected Redis client.  When ``None``, the wrapper behaves as a
        pass-through (no caching, no errors).
    ttl_seconds:
        Cache TTL.  Defaults to 30 minutes.
    """

    def __init__(
        self,
        base: object,
        redis_client: "redis_lib.Redis | None",
        ttl_seconds: int = _CACHE_TTL_SECONDS,
    ) -> None:
        self._base = base
        self._redis = redis_client
        self._ttl = ttl_seconds

    # ── Public interface (Retriever protocol) ──────────────────────────────────

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return cached chunks, or delegate to the base retriever and cache."""
        if self._redis is None:
            return self._base.search(question=question, collections=collections, top_k=top_k)  # type: ignore[union-attr]

        key = self._cache_key(question, collections, top_k)

        # ── Cache hit ──────────────────────────────────────────────────────────
        try:
            raw = self._redis.get(key)
            if raw:
                data = json.loads(raw)
                chunks = [RetrievedChunk.model_validate(d) for d in data]
                logger.info(
                    "Retrieval cache HIT  key=%.16s…  chunks=%d", key, len(chunks)
                )
                return chunks
        except Exception as exc:
            logger.debug("Retrieval cache get failed: %s", exc)

        # ── Cache miss — delegate to full retrieval stack ─────────────────────
        chunks = self._base.search(question=question, collections=collections, top_k=top_k)  # type: ignore[union-attr]

        try:
            payload = json.dumps([c.model_dump() for c in chunks])
            self._redis.set(key, payload, ex=self._ttl)
            logger.info(
                "Retrieval cache SET  key=%.16s…  chunks=%d  ttl=%ds",
                key, len(chunks), self._ttl,
            )
        except Exception as exc:
            logger.debug("Retrieval cache set failed: %s", exc)

        return chunks

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _cache_key(
        self,
        question: str,
        collections: list[str] | None,
        top_k: int,
    ) -> str:
        raw = f"{question.strip().lower()}|{sorted(collections or [])}|{top_k}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return f"{_KEY_PREFIX}:{digest}"

    def invalidate(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> None:
        """Explicitly remove a single cached result (e.g. after re-indexing)."""
        if self._redis is None:
            return
        key = self._cache_key(question, collections, top_k)
        try:
            self._redis.delete(key)
        except Exception as exc:
            logger.debug("Retrieval cache delete failed: %s", exc)
