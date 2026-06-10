"""Baseline RAG pipeline: vector search → Gemini → cited answer.

Purpose
-------
``BaselineRAGPipeline`` is the Phase 5 orchestrator. It wires together the
``QdrantRetriever`` and ``GeminiClient`` into a single ``run()`` call that
returns a structured ``RAGResponse``.

Architecture Integration
------------------------
* Phase 5: this file IS the pipeline. No agents, no hybrid search, no reranking.
* Phase 6+: ``BaselineRAGPipeline`` is replaced (not extended) by progressively
  more capable implementations:
  - Phase 6 swaps ``QdrantRetriever`` for a ``HybridRetriever``.
  - Phase 7 inserts a ``Reranker`` between retrieval and generation.
  - Phase 8 replaces this class with a LangGraph ``StateGraph`` that calls
    the same retriever and generation nodes directly.

Keeping this class thin (no business logic beyond orchestration) makes the
swap from Phase 5 → Phase 8 a clean replacement rather than a refactor.
"""

from __future__ import annotations

import logging
import time

from backend.app.schemas.rag import (
    ChatRequest,
    CitationSource,
    RAGResponse,
    RetrievedChunk,
)
from backend.app.services.generation import GeminiClient
from backend.app.services.retrieval import DEFAULT_RETRIEVAL_COLLECTIONS, Retriever

logger = logging.getLogger(__name__)

_NO_RESULTS_ANSWER: str = (
    "No relevant regulatory context was found for your question. "
    "Please ensure the knowledge base has been indexed, or try rephrasing."
)


class BaselineRAGPipeline:
    """Orchestrates retrieval + generation for compliance chat (Phase 5+).

    Accepts any ``Retriever``-protocol object — ``QdrantRetriever`` (Phase 5),
    ``HybridRetriever`` (Phase 6), or a reranking wrapper (Phase 7) — without
    requiring any changes to this class.

    Parameters
    ----------
    retriever:
        Any object satisfying the ``Retriever`` Protocol.
    gemini_client:
        ``GeminiClient`` instance for answer generation.
    """

    def __init__(
        self,
        retriever: Retriever,
        gemini_client: GeminiClient,
    ) -> None:
        self._retriever = retriever
        self._gemini = gemini_client

    def run(self, request: ChatRequest) -> RAGResponse:
        """Execute the full RAG pipeline for a compliance question.

        Steps
        -----
        1. Resolve target collections.
        2. Retrieve top-K chunks via semantic search.
        3. Return a no-results response if Qdrant returns nothing.
        4. Generate a cited answer with Gemini.
        5. Deduplicate retrieved chunks into a citation list.
        6. Return the structured ``RAGResponse``.
        """
        started_at = time.monotonic()

        collections = (
            [str(c) for c in request.collections]
            if request.collections
            else list(DEFAULT_RETRIEVAL_COLLECTIONS)
        )

        # ── Step 1: Retrieve ───────────────────────────────────────────────────
        chunks = self._retriever.search(
            question=request.question,
            collections=collections,
            top_k=request.top_k,
        )

        if not chunks:
            logger.warning(
                "No chunks retrieved for question: %.70s…", request.question
            )
            return RAGResponse(
                question=request.question,
                answer=_NO_RESULTS_ANSWER,
                sources=[],
                retrieved_chunks=[],
                chunks_used=0,
                latency_ms=_elapsed_ms(started_at),
                model=self._gemini.model_name,
                collections_searched=collections,
            )

        # ── Step 2: Generate ───────────────────────────────────────────────────
        answer = self._gemini.generate_compliance_answer(
            question=request.question,
            chunks=chunks,
        )

        # ── Step 3: Build citations ────────────────────────────────────────────
        sources = _deduplicate_citations(chunks)

        latency_ms = _elapsed_ms(started_at)
        logger.info(
            "RAG pipeline done in %.0fms — %d chunks, %d sources.",
            latency_ms,
            len(chunks),
            len(sources),
        )

        return RAGResponse(
            question=request.question,
            answer=answer,
            sources=sources,
            retrieved_chunks=chunks,
            chunks_used=len(chunks),
            latency_ms=latency_ms,
            model=self._gemini.active_model,  # reflects actual provider used
            collections_searched=collections,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _elapsed_ms(started_at: float) -> float:
    """Return milliseconds elapsed since ``started_at``."""
    return round((time.monotonic() - started_at) * 1000, 2)


def _deduplicate_citations(chunks: list[RetrievedChunk]) -> list[CitationSource]:
    """Build a deduplicated citation list from retrieved chunks.

    Two chunks from the same source document are collapsed into one citation.
    The deduplication key is ``(source_title, rule_reference, collection)``.
    """
    seen: set[tuple[str, str, str]] = set()
    citations: list[CitationSource] = []
    for chunk in chunks:
        key = (
            chunk.source_title or "",
            chunk.rule_reference or "",
            chunk.collection,
        )
        if key not in seen:
            seen.add(key)
            citations.append(
                CitationSource(
                    source_title=chunk.source_title or chunk.collection,
                    source_url=chunk.source_url,
                    rule_reference=chunk.rule_reference,
                    collection=chunk.collection,
                    authority=chunk.authority,
                )
            )
    return citations
