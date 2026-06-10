"""Shared constants for the ADGM Compliance Copilot backend.

This module centralizes stable names used across retrieval, indexing, and
future LangGraph workflows so collection names and supported file types do not
drift between services.
"""

from typing import Final

APP_NAME: Final[str] = "ADGM Compliance Copilot"

QDRANT_COLLECTION_REGULATIONS: Final[str] = "regulations"
QDRANT_COLLECTION_TEMPLATES: Final[str] = "templates"
QDRANT_COLLECTION_GUIDANCE: Final[str] = "guidance"
QDRANT_COLLECTION_CHECKLISTS: Final[str] = "checklists"
QDRANT_COLLECTION_HISTORICAL_REVIEWS: Final[str] = "historical_reviews"

QDRANT_COLLECTIONS: Final[tuple[str, ...]] = (
    QDRANT_COLLECTION_REGULATIONS,
    QDRANT_COLLECTION_TEMPLATES,
    QDRANT_COLLECTION_GUIDANCE,
    QDRANT_COLLECTION_CHECKLISTS,
    QDRANT_COLLECTION_HISTORICAL_REVIEWS,
)

SUPPORTED_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = (".pdf", ".docx")

