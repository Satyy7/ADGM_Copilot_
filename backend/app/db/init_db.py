"""Local database initialization helper.

This creates the current SQLAlchemy tables in PostgreSQL for local development.
Future production-grade schema changes should move to Alembic migrations.
"""

import logging

from backend.app.db.base import Base
from backend.app.db.postgres import get_postgres_engine

# Import models so their table metadata is registered with Base.
import backend.app.models  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all registered database tables if they do not already exist."""

    engine = get_postgres_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or already present.")


if __name__ == "__main__":
    init_db()
