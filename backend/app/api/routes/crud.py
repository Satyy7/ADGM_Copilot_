"""Small helper for creating CRUD routers.

These routes give the backend a usable persistence API before RAG, ingestion,
and agent workflows are introduced.
"""

from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.deps import get_session
from backend.app.db.base import Base
from backend.app.repositories import BaseRepository

ModelT = TypeVar("ModelT", bound=Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ReadSchemaT = TypeVar("ReadSchemaT", bound=BaseModel)


def build_crud_router(
    *,
    model: type[ModelT],
    create_schema: type[CreateSchemaT],
    update_schema: type[UpdateSchemaT] | None,
    read_schema: type[ReadSchemaT],
    prefix: str,
    tags: list[str],
) -> APIRouter:
    """Build a basic CRUD router for one persisted resource."""

    router = APIRouter(prefix=prefix, tags=tags)
    repository: BaseRepository[ModelT, CreateSchemaT, UpdateSchemaT] = BaseRepository(
        model
    )

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    def create_record(
        payload: create_schema,  # type: ignore[valid-type]
        session: Session = Depends(get_session),
    ) -> ModelT:
        """Create a record."""

        return repository.create(session, payload)

    @router.get("", response_model=list[read_schema])  # type: ignore[valid-type]
    def list_records(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
        session: Session = Depends(get_session),
    ) -> list[ModelT]:
        """List records."""

        return repository.list(session, offset=offset, limit=limit)

    @router.get("/{record_id}", response_model=read_schema)
    def get_record(
        record_id: UUID,
        session: Session = Depends(get_session),
    ) -> ModelT:
        """Get one record by ID."""

        record = repository.get(session, record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} not found.",
            )
        return record

    if update_schema is not None:

        @router.patch("/{record_id}", response_model=read_schema)
        def update_record(
            record_id: UUID,
            payload: update_schema,  # type: ignore[valid-type]
            session: Session = Depends(get_session),
        ) -> ModelT:
            """Partially update one record."""

            record = repository.get(session, record_id)
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} not found.",
                )
            return repository.update(session, record, payload)

    return router

