"""Pydantic schemas for the RAG pipeline (Phase 5+).

These schemas flow through all retrieval layers — baseline RAG (Phase 5),
hybrid search (Phase 6), re-ranking (Phase 7), and LangGraph nodes (Phase 8+).
Keeping them in one place prevents drift between phases.
"""

from __future__ import annotations

from pydantic import Field

from backend.app.schemas.base import SchemaBase
from backend.app.schemas.source import KnowledgeCollection


class ChatRequest(SchemaBase):
    """Incoming compliance question from the user."""

    question: str = Field(..., min_length=5, max_length=2000)
    collections: list[KnowledgeCollection] | None = Field(
        default=None,
        description=(
            "Qdrant collections to search. "
            "Defaults to regulations, guidance, and checklists when None."
        ),
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve and pass to the LLM.",
    )


class RetrievedChunk(SchemaBase):
    """One search result returned from Qdrant, enriched with citation metadata.

    Included in ``RAGResponse.retrieved_chunks`` so retrieval quality can be
    inspected directly from the API during Phase 5 validation.
    """

    chunk_id: str
    collection: str
    text: str
    score: float = Field(..., description="Cosine similarity score (0–1).")
    source_title: str | None = None
    source_url: str | None = None
    rule_reference: str | None = None
    page_number: int | None = None
    heading: str | None = None
    authority: str | None = None


class CitationSource(SchemaBase):
    """A deduplicated source reference included in the answer."""

    source_title: str
    source_url: str | None = None
    rule_reference: str | None = None
    collection: str
    authority: str | None = None


class RAGResponse(SchemaBase):
    """Full response returned by the compliance chat endpoint."""

    question: str
    answer: str
    sources: list[CitationSource]
    retrieved_chunks: list[RetrievedChunk] = Field(
        description="Raw chunks passed to the LLM — inspect for retrieval quality validation.",
    )
    chunks_used: int
    latency_ms: float
    model: str
    collections_searched: list[str]
