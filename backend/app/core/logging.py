"""Logging setup for backend services.

The FastAPI entry point calls this once at startup so all modules emit logs in a
consistent format during local development and later production deployment.
"""

import logging

from backend.app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure root logging for the application."""

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

