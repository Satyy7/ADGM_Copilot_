"""Shared SQLAlchemy declarative base.

All PostgreSQL models inherit from this base so local initialization and future
Alembic migrations can discover the complete compliance data model.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

