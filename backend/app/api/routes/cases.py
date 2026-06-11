"""Similar-case search API route — Phase 11.

Endpoint
--------
POST /cases/search  — embed a query and retrieve similar historical compliance cases
                      from the ``historical_reviews`` Qdrant collection.

The collection is populated automatically every time a document is analysed via
POST /reviews/analyze.  Cases accumulate over time and the search becomes
progressively more useful as the review history grows.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from backend.app.agent.cases.retriever import get_retriever
from backend.app.schemas.case_result import CaseSearchRequest, CaseSearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["Historical Cases"])


@router.post(
    "/search",
    response_model=CaseSearchResult,
    summary="Find similar historical compliance cases",
    description=(
        "Search the historical review database for past compliance cases semantically "
        "similar to your query. Useful for benchmarking a current review against how "
        "similar documents were assessed, what violations were found, and what ADGM "
        "regulations were most frequently cited."
    ),
)
def search_similar_cases(request: CaseSearchRequest) -> CaseSearchResult:
    """Phase 11: embed query -> search historical_reviews -> return similar cases."""
    try:
        retriever = get_retriever()
        cases = retriever.search(query=request.query, top_k=request.top_k)
    except Exception as exc:
        logger.error("Similar-case search failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Case search failed: {exc}",
        ) from exc

    return CaseSearchResult(
        query=request.query,
        results=cases,
        count=len(cases),
    )
