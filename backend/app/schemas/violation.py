"""Violation API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class ViolationCreate(SchemaBase):
    """Request body for recording a detected compliance violation."""

    review_id: UUID
    violation_type: str = Field(..., max_length=150)
    severity: str = Field(..., max_length=50)
    title: str = Field(..., max_length=300)
    description: str
    regulation_reference: str | None = Field(default=None, max_length=300)
    document_excerpt: str | None = None
    evidence_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    status: str = Field(default="open", max_length=50)


class ViolationUpdate(SchemaBase):
    """Mutable violation fields."""

    severity: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    regulation_reference: str | None = Field(default=None, max_length=300)
    document_excerpt: str | None = None
    evidence_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    status: str | None = Field(default=None, max_length=50)


class ViolationRead(IdentifierSchema, TimestampSchema):
    """Violation response schema."""

    review_id: UUID
    violation_type: str
    severity: str
    title: str
    description: str
    regulation_reference: str | None
    document_excerpt: str | None
    evidence_payload: JsonDict | None
    citation_payload: JsonDict | None
    status: str

