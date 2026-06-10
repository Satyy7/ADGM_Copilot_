"""Qdrant client helpers.

Qdrant stores embeddings for regulations, templates, guidance, checklists, and
historical reviews. Retrieval and ingestion services should use this module
instead of constructing clients directly.
"""

from functools import lru_cache

from qdrant_client import QdrantClient

from backend.app.core.config import Settings, get_settings


def create_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    """Create a Qdrant client from application settings."""

    resolved_settings = settings or get_settings()
    api_key = (
        resolved_settings.qdrant_api_key.get_secret_value()
        if resolved_settings.qdrant_api_key is not None
        else None
    )
    return QdrantClient(
        host=resolved_settings.qdrant_host,
        port=resolved_settings.qdrant_port,
        grpc_port=resolved_settings.qdrant_grpc_port,
        api_key=api_key,
        https=resolved_settings.qdrant_https,
    )


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Return the shared Qdrant client."""

    return create_qdrant_client()


def check_qdrant_health() -> bool:
    """Return True when Qdrant responds to a collection listing request."""

    try:
        get_qdrant_client().get_collections()
        return True
    except Exception:
        return False
