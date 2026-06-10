"""User API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import IdentifierSchema, SchemaBase, TimestampSchema


class UserCreate(SchemaBase):
    """Request body for creating an application user."""

    email: str = Field(..., max_length=320)
    full_name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=100)


class UserUpdate(SchemaBase):
    """Request body for updating user profile metadata."""

    full_name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class UserRead(IdentifierSchema, TimestampSchema):
    """User response schema."""

    id: UUID
    email: str
    full_name: str | None
    organization: str | None
    role: str | None
    is_active: bool

