"""Repository layer for database access.

Repositories keep FastAPI routes thin and give future service/RAG workflows a
single place to persist and read compliance platform records.
"""

from backend.app.repositories.base import BaseRepository

__all__ = ["BaseRepository"]

