"""Recommendation API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class RecommendationCreate(SchemaBase):
    """Request body for recording a compliance recommendation."""

    review_id: UUID
    violation_id: UUID | None = None
    title: str = Field(..., max_length=300)
    recommendation_text: str
    priority: str = Field(default="medium", max_length=50)
    citation_payload: JsonDict | None = None
    status: str = Field(default="open", max_length=50)


class RecommendationUpdate(SchemaBase):
    """Mutable recommendation fields."""

    title: str | None = Field(default=None, max_length=300)
    recommendation_text: str | None = None
    priority: str | None = Field(default=None, max_length=50)
    citation_payload: JsonDict | None = None
    status: str | None = Field(default=None, max_length=50)


class RecommendationRead(IdentifierSchema, TimestampSchema):
    """Recommendation response schema."""

    review_id: UUID
    violation_id: UUID | None
    title: str
    recommendation_text: str
    priority: str
    citation_payload: JsonDict | None
    status: str

