"""Compliance review report schemas — Phase 9 output contract.

These schemas represent the AI-generated review report returned by
POST /api/v1/reviews/analyze. They are distinct from the CRUD schemas
in review.py which represent DB-persisted review records.
"""

from __future__ import annotations

from backend.app.schemas.base import SchemaBase


class DetectedViolation(SchemaBase):
    """One compliance violation found in the reviewed document."""

    clause_heading: str
    clause_excerpt: str
    violation_type: str   # non_compliant_clause | missing_disclosure | inadequate_provision | prohibited_term
    severity: str         # high | medium | low
    title: str
    description: str
    regulation_reference: str | None = None
    recommendation: str


class IdentifiedGap(SchemaBase):
    """A required provision that is absent from the document."""

    missing_provision: str
    severity: str         # high | medium | low
    regulation_reference: str | None = None
    recommendation: str


class ReviewReport(SchemaBase):
    """Full AI-generated compliance review report."""

    document_name: str
    document_type: str
    compliance_score: float         # 0–100
    summary: str
    violations: list[DetectedViolation]
    gaps: list[IdentifiedGap]
    total_issues: int               # len(violations) + len(gaps)
    model: str
    latency_ms: float
