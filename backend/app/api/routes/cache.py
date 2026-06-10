"""Cache management endpoints — Phase 16.

Endpoints
---------
GET  /api/v1/cache/stats              — key counts per namespace + Redis memory info
DELETE /api/v1/cache/flush/{namespace} — delete all keys in a namespace
DELETE /api/v1/cache/flush             — delete ALL cache keys (all namespaces)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.db.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache"])

# Known namespaces and their key patterns
_NAMESPACES: dict[str, str] = {
    "embeddings":    "embed:*",
    "generate_text": "gentext:*",
    "retrieval":     "retrieval:*",
}


def _count_keys(redis, pattern: str) -> int:
    """Count Redis keys matching *pattern* via SCAN (non-blocking)."""
    count = 0
    try:
        cursor = 0
        while True:
            cursor, keys = redis.scan(cursor=cursor, match=pattern, count=500)
            count += len(keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Redis SCAN failed for pattern %s: %s", pattern, exc)
    return count


def _delete_keys(redis, pattern: str) -> int:
    """Delete all Redis keys matching *pattern*. Returns number deleted."""
    deleted = 0
    try:
        cursor = 0
        while True:
            cursor, keys = redis.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Redis bulk delete failed for pattern %s: %s", pattern, exc)
    return deleted


@router.get("/stats")
def get_cache_stats() -> dict:
    """Return key counts per cache namespace and Redis memory stats."""
    redis = get_redis_client()

    namespace_counts: dict[str, int] = {}
    for name, pattern in _NAMESPACES.items():
        namespace_counts[name] = _count_keys(redis, pattern)

    total_cached = sum(namespace_counts.values())

    # Redis memory info (subset of INFO memory)
    memory_info: dict[str, str] = {}
    try:
        info = redis.info("memory")
        memory_info = {
            "used_memory_human":     info.get("used_memory_human", "?"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "?"),
            "maxmemory_human":       info.get("maxmemory_human", "0B"),
        }
    except Exception as exc:
        logger.warning("Redis INFO failed: %s", exc)

    return {
        "namespaces": namespace_counts,
        "total_cached_keys": total_cached,
        "ttl_seconds": {
            "embeddings":    60 * 60 * 24 * 7,  # 7 days
            "generate_text": 60 * 60,            # 1 hour
            "retrieval":     60 * 30,            # 30 minutes
        },
        "memory": memory_info,
    }


@router.delete("/flush/{namespace}")
def flush_namespace(namespace: str) -> dict:
    """Delete all cache keys in a single namespace.

    Valid namespaces: ``embeddings``, ``generate_text``, ``retrieval``.
    """
    if namespace not in _NAMESPACES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown namespace '{namespace}'. Valid: {list(_NAMESPACES)}",
        )
    redis = get_redis_client()
    pattern = _NAMESPACES[namespace]
    deleted = _delete_keys(redis, pattern)
    logger.info("Cache flush: namespace=%s  deleted=%d keys", namespace, deleted)
    return {"namespace": namespace, "deleted_keys": deleted}


@router.delete("/flush")
def flush_all_caches() -> dict:
    """Delete ALL cache keys across every namespace."""
    redis = get_redis_client()
    results: dict[str, int] = {}
    for name, pattern in _NAMESPACES.items():
        results[name] = _delete_keys(redis, pattern)
    total = sum(results.values())
    logger.info("Cache flush ALL: deleted %d keys total", total)
    return {"deleted_by_namespace": results, "total_deleted": total}
