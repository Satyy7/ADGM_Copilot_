"""Text2SQL analytics schemas — Phase 12."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from backend.app.schemas.base import SchemaBase


class AnalyticsRequest(SchemaBase):
    """Request payload for the compliance analytics endpoint."""

    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Natural language analytics question about compliance data.",
    )
    preview_only: bool = Field(
        default=False,
        description=(
            "When True, return the generated SQL for human review without executing it. "
            "Use this to verify the SQL before running it against the database."
        ),
    )
    confirmed_sql: str | None = Field(
        default=None,
        description=(
            "Provide a reviewed/corrected SQL string to execute directly, "
            "bypassing the LLM generation step. Must still pass safety validation."
        ),
    )


class AnalyticsResult(SchemaBase):
    """Response from the compliance analytics endpoint."""

    question: str
    generated_sql: str
    sql_safe: bool
    sql_rejection_reason: str | None = None
    query_results: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    columns: list[str] = Field(default_factory=list)
    answer: str
    preview_only: bool
    model: str
    latency_ms: float
