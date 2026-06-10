"""Query log API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class QueryLogCreate(SchemaBase):
    """Request body for recording a chat, retrieval, or analytics query."""

    user_id: UUID | None = None
    query_type: str = Field(..., max_length=100)
    question: str
    response_text: str | None = None
    generated_sql: str | None = None
    sql_approved: bool | None = None
    sql_executed: bool | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    model_name: str | None = Field(default=None, max_length=150)
    retrieval_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    error_message: str | None = None


class QueryLogUpdate(SchemaBase):
    """Mutable query log fields."""

    response_text: str | None = None
    generated_sql: str | None = None
    sql_approved: bool | None = None
    sql_executed: bool | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    retrieval_payload: JsonDict | None = None
    citation_payload: JsonDict | None = None
    error_message: str | None = None


class QueryLogRead(IdentifierSchema, TimestampSchema):
    """Query log response schema."""

    user_id: UUID | None
    query_type: str
    question: str
    response_text: str | None
    generated_sql: str | None
    sql_approved: bool | None
    sql_executed: bool | None
    latency_ms: int | None
    model_name: str | None
    retrieval_payload: JsonDict | None
    citation_payload: JsonDict | None
    error_message: str | None

