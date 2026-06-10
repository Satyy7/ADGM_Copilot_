"""Aggregated infrastructure health checks.

The FastAPI health endpoint uses this module to verify Phase 1 services:
PostgreSQL, Qdrant, and Redis.
"""

from pydantic import BaseModel

from backend.app.db.postgres import check_postgres_health
from backend.app.db.qdrant import check_qdrant_health
from backend.app.db.redis import check_redis_health


class ServiceHealth(BaseModel):
    """Health status for one infrastructure service."""

    name: str
    healthy: bool


class HealthReport(BaseModel):
    """Combined infrastructure health report."""

    healthy: bool
    services: list[ServiceHealth]


def check_infrastructure_health() -> HealthReport:
    """Check all required local infrastructure services."""

    services = [
        ServiceHealth(name="postgres", healthy=check_postgres_health()),
        ServiceHealth(name="qdrant", healthy=check_qdrant_health()),
        ServiceHealth(name="redis", healthy=check_redis_health()),
    ]
    return HealthReport(
        healthy=all(service.healthy for service in services),
        services=services,
    )

