"""Similar-case retriever — Phase 11.

Searches the ``historical_reviews`` Qdrant collection to find past compliance
reviews that are semantically similar to a given query.

Unlike the main retrieval stack (Hybrid + BM25 + Re-rank), similar-case search
uses pure dense search because:
- Historical reviews are full narrative documents, not short regulatory chunks
- BM25 on review summaries adds little over semantic search
- The collection grows dynamically via indexing, so a static BM25 index won't work
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from backend.app.schemas.case_result import SimilarCase
from backend.app.services.embeddings import EmbeddingTaskType

if TYPE_CHECKING:
    from qdrant_client import QdrantClient
    from backend.app.services.embeddings import EmbeddingsService

logger = logging.getLogger(__name__)

_COLLECTION = "historical_reviews"


class SimilarCasesRetriever:
    """Retrieve historical compliance cases similar to a given query."""

    def __init__(self, qdrant: "QdrantClient", embeddings: "EmbeddingsService") -> None:
        self._qdrant = qdrant
        self._embeddings = embeddings

    def search(self, query: str, top_k: int = 5) -> list[SimilarCase]:
        """Embed the query and return up to ``top_k`` similar historical cases.

        Returns an empty list if the collection is missing or has no data.
        Never raises.
        """
        try:
            vector = self._embeddings.embed_text(query, EmbeddingTaskType.RETRIEVAL_QUERY)
            response = self._qdrant.query_points(
                collection_name=_COLLECTION,
                query=vector,
                limit=top_k,
                with_payload=True,
            )
            cases = [_point_to_case(hit) for hit in response.points]
            logger.info("Similar-case search returned %d results.", len(cases))
            return cases
        except Exception as exc:
            logger.warning("Similar-case search failed: %s", exc)
            return []


@lru_cache(maxsize=1)
def get_retriever() -> SimilarCasesRetriever:
    """Return the shared similar-cases retriever (cached per process)."""
    from backend.app.core.config import get_settings
    from backend.app.db.qdrant import get_qdrant_client
    from backend.app.services.embeddings import get_embeddings_service

    return SimilarCasesRetriever(
        qdrant=get_qdrant_client(),
        embeddings=get_embeddings_service(settings=get_settings()),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _point_to_case(hit: object) -> SimilarCase:
    """Convert a Qdrant ScoredPoint to a SimilarCase schema object."""
    payload: dict = getattr(hit, "payload", {}) or {}
    score: float = float(getattr(hit, "score", 0.0) or 0.0)
    return SimilarCase(
        document_type=payload.get("document_type", "unknown"),
        document_name=payload.get("document_name", "unknown"),
        compliance_score=float(payload.get("compliance_score", 0.0)),
        violation_count=int(payload.get("violation_count", 0)),
        gap_count=int(payload.get("gap_count", 0)),
        summary=payload.get("summary", ""),
        violation_types=payload.get("violation_types", []),
        regulation_references=payload.get("regulation_references", []),
        similarity_score=round(score, 4),
    )
