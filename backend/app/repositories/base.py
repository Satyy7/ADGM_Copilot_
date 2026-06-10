"""Generic SQLAlchemy repository helpers.

This layer intentionally stays small: it supports the basic persistence
operations needed before RAG services are introduced.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseRepository(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """Reusable CRUD operations for SQLAlchemy models."""

    def __init__(self, model: type[ModelT]) -> None:
        """Initialize the repository with an ORM model class."""

        self.model = model

    def get(self, session: Session, record_id: UUID) -> ModelT | None:
        """Return one record by primary key."""

        return session.get(self.model, record_id)

    def list(
        self,
        session: Session,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ModelT]:
        """Return a paginated list of records."""

        statement = select(self.model).offset(offset).limit(limit)
        return list(session.scalars(statement).all())

    def create(self, session: Session, payload: CreateSchemaT) -> ModelT:
        """Create and persist a record from a Pydantic schema."""

        record = self.model(**payload.model_dump(exclude_unset=True))
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def update(
        self,
        session: Session,
        record: ModelT,
        payload: UpdateSchemaT,
    ) -> ModelT:
        """Apply partial updates from a Pydantic schema."""

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, field, value)
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def delete(self, session: Session, record: ModelT) -> None:
        """Delete a persisted record."""

        session.delete(record)
        session.commit()

    def filter_by(
        self,
        session: Session,
        *,
        filters: dict[str, Any],
        offset: int = 0,
        limit: int = 50,
    ) -> list[ModelT]:
        """Return records matching simple equality filters."""

        statement = select(self.model).filter_by(**filters).offset(offset).limit(limit)
        return list(session.scalars(statement).all())
