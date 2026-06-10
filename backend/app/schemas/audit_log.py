"""Audit log API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class AuditLogCreate(SchemaBase):
    """Request body for recording an auditable action."""

    user_id: UUID | None = None
    action: str = Field(..., max_length=150)
    resource_type: str | None = Field(default=None, max_length=100)
    resource_id: str | None = Field(default=None, max_length=100)
    actor_ip: str | None = Field(default=None, max_length=64)
    details: JsonDict | None = None


class AuditLogRead(IdentifierSchema, TimestampSchema):
    """Audit log response schema."""

    user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    actor_ip: str | None
    details: JsonDict | None

