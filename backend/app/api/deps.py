"""FastAPI dependencies shared by API routes."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.app.db.postgres import get_db_session


def get_session() -> Generator[Session, None, None]:
    """Yield a PostgreSQL session for route handlers."""

    yield from get_db_session()

