"""Redis client helpers.

Redis is reserved for later caching of embeddings, retrieval results, and LLM
responses. Keeping the client centralized makes that caching layer easy to add.
"""

from functools import lru_cache

from redis import Redis

from backend.app.core.config import Settings, get_settings


def create_redis_client(settings: Settings | None = None) -> Redis:
    """Create a Redis client from application settings."""

    resolved_settings = settings or get_settings()
    return Redis.from_url(
        resolved_settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


@lru_cache
def get_redis_client() -> Redis:
    """Return the shared Redis client."""

    return create_redis_client()


def check_redis_health() -> bool:
    """Return True when Redis responds to PING."""

    try:
        return bool(get_redis_client().ping())
    except Exception:
        return False
