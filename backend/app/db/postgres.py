"""PostgreSQL connection management.

This module owns the SQLAlchemy engine and session factory used by future
models, repositories, analytics, and audit logging.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings, get_settings


def create_postgres_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL."""

    resolved_settings = settings or get_settings()
    return create_engine(
        resolved_settings.postgres_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache
def get_postgres_engine() -> Engine:
    """Return the shared PostgreSQL engine."""

    return create_postgres_engine()


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""

    session_factory = sessionmaker(
        bind=get_postgres_engine(),
        autoflush=False,
        autocommit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_postgres_health() -> bool:
    """Return True when PostgreSQL accepts a simple query."""

    try:
        with get_postgres_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
