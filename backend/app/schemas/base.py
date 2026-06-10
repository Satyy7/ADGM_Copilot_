"""Shared Pydantic schema primitives.

These base models keep FastAPI request and response contracts consistent across
review, chat, clause generation, and analytics APIs.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

JsonDict = dict[str, Any]


class SchemaBase(BaseModel):
    """Base schema with ORM serialization enabled."""

    model_config = ConfigDict(from_attributes=True)


class IdentifierSchema(SchemaBase):
    """Common UUID identifier field."""

    id: UUID


class TimestampSchema(SchemaBase):
    """Common timestamp fields returned by persisted resources."""

    created_at: datetime
    updated_at: datetime

