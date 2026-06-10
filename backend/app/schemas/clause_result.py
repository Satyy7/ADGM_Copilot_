"""Clause generation request and result schemas — Phase 10."""

from __future__ import annotations

from pydantic import Field

from backend.app.schemas.base import SchemaBase
from backend.app.schemas.rag import CitationSource


class ClauseRequest(SchemaBase):
    """Input for the clause generation endpoint."""

    request: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description=(
            "Natural language description of the clause to generate. "
            "E.g. 'Draft a UBO beneficial ownership disclosure clause for an ADGM private company.'"
        ),
    )
    document_type: str | None = Field(
        default=None,
        description=(
            "Optional hint for the target document type "
            "(articles_of_association, employment_contract, shareholders_agreement, etc.)."
        ),
    )
    top_k: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Number of regulatory/template chunks to retrieve as drafting context.",
    )


class ClauseResult(SchemaBase):
    """AI-generated ADGM-compliant clause with inline citations."""

    request: str
    clause_type: str
    document_type: str
    clause_text: str
    citations: list[CitationSource]
    model: str
    latency_ms: float
