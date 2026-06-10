"""Generated clause API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class GeneratedClauseCreate(SchemaBase):
    """Request body for storing a generated clause."""

    user_id: UUID | None = None
    request_text: str
    clause_type: str | None = Field(default=None, max_length=150)
    generated_text: str
    model_name: str | None = Field(default=None, max_length=150)
    retrieval_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    validation_status: str = Field(default="pending", max_length=50)


class GeneratedClauseUpdate(SchemaBase):
    """Mutable generated clause fields."""

    generated_text: str | None = None
    retrieval_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    validation_status: str | None = Field(default=None, max_length=50)


class GeneratedClauseRead(IdentifierSchema, TimestampSchema):
    """Generated clause response schema."""

    user_id: UUID | None
    request_text: str
    clause_type: str | None
    generated_text: str
    model_name: str | None
    retrieval_payload: JsonDict | None
    citation_payload: JsonDict | None
    validation_status: str

