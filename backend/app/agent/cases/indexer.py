"""Historical review indexer — Phase 11.

Indexes completed compliance review reports into the ``historical_reviews``
Qdrant collection so they can be retrieved as similar cases for future reviews.

Each indexed point stores:
- A rich text embedding of the review (doc type + violations + summary)
- Full metadata as Qdrant payload for display in the API response

The collection is created automatically on first use.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING

from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.services.embeddings import EMBEDDING_DIMENSION, EmbeddingTaskType

if TYPE_CHECKING:
    from qdrant_client import QdrantClient
    from backend.app.schemas.review_report import ReviewReport
    from backend.app.services.embeddings import EmbeddingsService

logger = logging.getLogger(__name__)

_COLLECTION = "historical_reviews"


class HistoricalReviewIndexer:
    """Embed and upsert a compliance review report into the historical_reviews collection."""

    def __init__(self, qdrant: "QdrantClient", embeddings: "EmbeddingsService") -> None:
        self._qdrant = qdrant
        self._embeddings = embeddings
        self._collection_ensured = False

    def index(self, report: "ReviewReport") -> str | None:
        """Embed and upsert a review report.

        Returns the Qdrant point ID on success, None on failure.
        Never raises — indexing must not fail the HTTP response.
        """
        try:
            self._ensure_collection()
            text = _build_review_text(report)
            vector = self._embeddings.embed_text(text, EmbeddingTaskType.RETRIEVAL_DOCUMENT)
            point_id = _point_id(report)
            payload: dict = {
                "document_name":         report.document_name,
                "document_type":         report.document_type,
                "compliance_score":      report.compliance_score,
                "violation_count":       len(report.violations),
                "gap_count":             len(report.recommendations),
                "violation_types":       list({v.violation_type for v in report.violations}),
                "regulation_references": list({
                    v.regulation_reference
                    for v in report.violations
                    if v.regulation_reference
                }),
                "summary":               report.summary,
                "text":                  text,
            }
            self._qdrant.upsert(
                collection_name=_COLLECTION,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
            logger.info("Indexed review '%s' as point %s.", report.document_name, point_id)
            return point_id
        except Exception as exc:
            logger.warning("Failed to index review '%s': %s", report.document_name, exc)
            return None

    def _ensure_collection(self) -> None:
        """Create the historical_reviews collection if it does not exist."""
        if self._collection_ensured:
            return
        existing = {c.name for c in self._qdrant.get_collections().collections}
        if _COLLECTION not in existing:
            self._qdrant.create_collection(
                collection_name=_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'.", _COLLECTION)
        self._collection_ensured = True


@lru_cache(maxsize=1)
def get_indexer() -> HistoricalReviewIndexer:
    """Return the shared indexer (cached per process)."""
    from backend.app.core.config import get_settings
    from backend.app.db.qdrant import get_qdrant_client
    from backend.app.services.embeddings import get_embeddings_service

    return HistoricalReviewIndexer(
        qdrant=get_qdrant_client(),
        embeddings=get_embeddings_service(settings=get_settings()),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_review_text(report: "ReviewReport") -> str:
    """Build a rich text representation of a review suitable for embedding."""
    parts = [
        f"Document type: {report.document_type}",
        f"Compliance score: {report.compliance_score:.0f}/100",
        f"Summary: {report.summary}",
    ]
    if report.violations:
        v_lines = [
            f"[{v.severity.upper()}] {v.title}: {v.description[:120]}"
            for v in report.violations[:5]
        ]
        parts.append("Violations:\n" + "\n".join(v_lines))
    if report.recommendations:
        g_lines = [f"- {r.title}" for r in report.recommendations[:5]]
        parts.append("Missing provisions:\n" + "\n".join(g_lines))
    return "\n".join(parts)


def _point_id(report: "ReviewReport") -> str:
    """Deterministic UUID from document name + score + issue count."""
    raw = f"{report.document_name}|{report.compliance_score}|{len(report.violations) + len(report.recommendations)}"
    hex_digest = hashlib.sha256(raw.encode()).hexdigest()
    return str(uuid.UUID(hex_digest[:32]))
