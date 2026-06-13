"""FastAPI entry point for ADGM Compliance Copilot.

This file wires core settings, logging, and infrastructure health checks into a
minimal API shell. Future routers for review, chat, clause generation, and
analytics will register here after their lower-level services are validated.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.db.health import HealthReport, check_infrastructure_health
from backend.app.db.init_db import init_db

settings = get_settings()
configure_logging(settings)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    """Create database tables if they do not already exist."""
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", response_model=HealthReport)
def health_check() -> HealthReport:
    """Return health status for PostgreSQL, Qdrant, and Redis."""

    return check_infrastructure_health()
