"""Similar case retrieval schemas — Phase 11."""

from __future__ import annotations

from pydantic import Field

from backend.app.schemas.base import SchemaBase


class SimilarCase(SchemaBase):
    """A historical compliance review case similar to the current query."""

    document_type: str
    document_name: str
    compliance_score: float
    violation_count: int
    gap_count: int
    summary: str
    violation_types: list[str] = Field(default_factory=list)
    regulation_references: list[str] = Field(default_factory=list)
    similarity_score: float          # cosine similarity from Qdrant, 0-1


class CaseSearchRequest(SchemaBase):
    """Request payload for the similar-case search endpoint."""

    query: str = Field(..., min_length=5, max_length=2000)
    document_type: str | None = None   # optional filter hint
    top_k: int = Field(default=5, ge=1, le=20)


class CaseSearchResult(SchemaBase):
    """Response from the similar-case search endpoint."""

    query: str
    similar_cases: list[SimilarCase]
    total_found: int
