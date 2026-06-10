"""Compliance review API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class ReviewCreate(SchemaBase):
    """Request body for starting or recording a compliance review."""

    document_id: UUID
    user_id: UUID | None = None
    review_type: str = Field(..., max_length=100)
    status: str = Field(default="pending", max_length=50)
    started_at: datetime | None = None


class ReviewUpdate(SchemaBase):
    """Mutable compliance review fields."""

    status: str | None = Field(default=None, max_length=50)
    compliance_score: Decimal | None = Field(default=None, ge=0, le=100)
    summary: str | None = None
    evidence_payload: JsonDict | None = None
    report_payload: JsonDict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ReviewRead(IdentifierSchema, TimestampSchema):
    """Compliance review response schema."""

    document_id: UUID
    user_id: UUID | None
    review_type: str
    status: str
    compliance_score: Decimal | None
    summary: str | None
    evidence_payload: JsonDict | None
    report_payload: JsonDict | None
    started_at: datetime | None
    completed_at: datetime | None

