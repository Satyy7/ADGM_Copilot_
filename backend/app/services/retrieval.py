"""Qdrant vector search retrieval service + Retriever Protocol.

Purpose
-------
Provides ``QdrantRetriever``, which embeds a question and searches one or more
Qdrant collections, merges the results by cosine score, deduplicates by
chunk ID, and returns the top-K ``RetrievedChunk`` objects.

Also exports the ``Retriever`` Protocol so that ``BaselineRAGPipeline`` and
future agents accept any retriever (Qdrant, BM25, Hybrid, mock) without
importing a concrete class — enabling clean Phase 6/7/8 upgrades.

Architecture Integration
------------------------
* Phase 5 (baseline): ``QdrantRetriever`` used directly by ``BaselineRAGPipeline``.
* Phase 6 (hybrid search): ``HybridRetriever`` satisfies ``Retriever``; pipeline
  code requires no changes beyond the factory in ``chat.py``.
* Phase 7 (re-ranking): ``RerankedRetriever`` wraps ``HybridRetriever`` and also
  satisfies ``Retriever`` — same swap pattern.
* Phase 8+ (LangGraph): ``Retriever`` is the type annotation on the tool node.
"""

from __future__ import annotations

import logging
from typing import Protocol

from qdrant_client import QdrantClient

from backend.app.schemas.rag import RetrievedChunk
from backend.app.services.embeddings import EmbeddingTaskType, EmbeddingsService

logger = logging.getLogger(__name__)

DEFAULT_RETRIEVAL_COLLECTIONS: tuple[str, ...] = (
    "regulations",
    "guidance",
    "checklists",
)
"""Collections searched when the caller does not supply a list.

``templates`` is omitted from chat defaults (it's used by the clause
generator). ``historical_reviews`` is omitted until Phase 11 populates it.
"""

_CANDIDATE_MULTIPLIER: int = 3
"""Search this many candidates per collection before the cross-collection merge.

Example: top_k=5 with 3 collections → 15 candidates → dedup → top 5.
This improves inter-collection ranking without adding extra API calls.
"""


class QdrantRetriever:
    """Semantic search over one or more Qdrant collections.

    Parameters
    ----------
    qdrant_client:
        Connected ``QdrantClient`` instance (from ``get_qdrant_client()``).
    embeddings_service:
        ``EmbeddingsService`` used to embed the query at search time.
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embeddings_service: EmbeddingsService,
    ) -> None:
        self._qdrant = qdrant_client
        self._embeddings = embeddings_service

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Embed ``question`` and retrieve the top-K chunks from Qdrant.

        Searches each collection independently, merges the candidates by
        cosine score, deduplicates, and returns the top ``top_k`` results.

        Parameters
        ----------
        question:
            Natural language compliance question.
        collections:
            Collections to search. Defaults to ``DEFAULT_RETRIEVAL_COLLECTIONS``.
        top_k:
            Final number of chunks to return after cross-collection merge.
        """
        target_collections = collections or list(DEFAULT_RETRIEVAL_COLLECTIONS)
        candidates_per_collection = max(top_k, top_k * _CANDIDATE_MULTIPLIER)

        query_vector = self._embeddings.embed_text(
            question,
            task_type=EmbeddingTaskType.RETRIEVAL_QUERY,
        )

        all_results: list[RetrievedChunk] = []
        for collection in target_collections:
            try:
                hits = self._search_collection(query_vector, collection, candidates_per_collection)
                all_results.extend(hits)
                logger.debug("Collection '%s': %d candidates.", collection, len(hits))
            except Exception as exc:
                logger.warning(
                    "Search failed for collection '%s' (skipping): %s",
                    collection,
                    exc,
                )

        merged = self._merge_and_deduplicate(all_results, top_k)
        logger.info(
            "Retrieved %d chunks from %s for: %.70s…",
            len(merged),
            target_collections,
            question,
        )
        return merged

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _search_collection(
        self,
        query_vector: list[float],
        collection_name: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        """Run a single-collection vector search and map to ``RetrievedChunk``."""
        response = self._qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )

        chunks: list[RetrievedChunk] = []
        for hit in response.points:
            payload = hit.payload or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(hit.id)),
                    collection=payload.get("collection", collection_name),
                    text=payload.get("text", ""),
                    score=round(float(hit.score), 6),
                    source_title=payload.get("source_title"),
                    source_url=payload.get("canonical_url") or payload.get("source_url"),
                    rule_reference=payload.get("rule_reference"),
                    page_number=payload.get("page_number"),
                    heading=payload.get("heading"),
                    authority=payload.get("authority"),
                )
            )
        return chunks

    @staticmethod
    def _merge_and_deduplicate(
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Sort by score desc, deduplicate by chunk_id, return top_k."""
        seen_ids: set[str] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in sorted(chunks, key=lambda c: c.score, reverse=True):
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                deduped.append(chunk)
        return deduped[:top_k]


# ── Retriever Protocol ─────────────────────────────────────────────────────────

class Retriever(Protocol):
    """Structural interface satisfied by any retriever implementation.

    Using a Protocol (PEP 544) rather than an ABC lets ``QdrantRetriever``,
    ``BM25Retriever``, ``HybridRetriever``, and any future retriever satisfy
    the interface without inheriting from a base class — ideal for duck-typed
    dependency injection and LangGraph node composition.

    Any object with a matching ``search`` signature satisfies this Protocol.
    """

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Retrieve the top-K most relevant chunks for ``question``."""
        ...
