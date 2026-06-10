"""Compliance chat API route — Phase 8 LangGraph intent router.

Purpose
-------
Exposes ``POST /api/v1/chat`` as the single entry point for all compliance
queries. The endpoint hands the request to the LangGraph workflow graph which:

1. Classifies the question intent (compliance_chat / review / clause / analytics)
2. Routes it to the appropriate capability path
3. Returns a structured ``RAGResponse``

The endpoint signature (``ChatRequest`` in, ``RAGResponse`` out) has not changed
since Phase 5 — the frontend requires no modifications.

Architecture Integration
------------------------
* Phase 8: LangGraph ``StateGraph`` replaces ``BaselineRAGPipeline`` as the
  execution backbone. ``BaselineRAGPipeline`` is retained for direct testing.
* Phase 9+: new capability nodes are added to the graph in ``graph.py``; this
  file never needs to change again.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.agent.graph import get_compiled_graph
from backend.app.agent.state import initial_state
from backend.app.api.deps import get_session
from backend.app.models.query_log import QueryLog
from backend.app.repositories.base import BaseRepository
from backend.app.schemas.query_log import QueryLogCreate
from backend.app.schemas.rag import ChatRequest, RAGResponse

router = APIRouter(prefix="/chat", tags=["Compliance Chat"])
logger = logging.getLogger(__name__)

_query_log_repo: BaseRepository = BaseRepository(QueryLog)


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=RAGResponse,
    summary="Compliance chat",
    description=(
        "Ask a natural language compliance question. "
        "The LangGraph intent router classifies the query and dispatches it "
        "to the appropriate capability (chat, review, clause generation, analytics)."
    ),
)
def compliance_chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
) -> RAGResponse:
    """Phase 8: intent router → retrieve → re-rank → Gemini/Groq → cited answer."""
    started_at = time.monotonic()

    collections = (
        [str(c) for c in request.collections] if request.collections else None
    )

    try:
        graph = get_compiled_graph()
        state = initial_state(
            question=request.question,
            collections=collections,
            top_k=request.top_k,
        )
        final_state = graph.invoke(state)  # type: ignore[union-attr]
    except Exception as exc:
        logger.error("Compliance graph failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance chat failed: {exc}",
        ) from exc

    latency_ms = round((time.monotonic() - started_at) * 1000, 2)
    response = _build_response(final_state, request, latency_ms)

    _persist_query_log(session, request, response)
    return response


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_response(
    state: dict,
    request: ChatRequest,
    latency_ms: float,
) -> RAGResponse:
    """Convert a completed ``AgentState`` dict into a ``RAGResponse``."""
    chunks = state.get("retrieved_chunks", [])
    return RAGResponse(
        question=state.get("question", request.question),
        answer=state.get("answer", ""),
        sources=state.get("sources", []),
        retrieved_chunks=chunks,
        chunks_used=len(chunks),
        latency_ms=latency_ms,
        model=state.get("model", "unknown"),
        collections_searched=state.get("collections_searched", []),
    )


def _persist_query_log(
    session: Session,
    request: ChatRequest,
    response: RAGResponse,
) -> None:
    """Write the query and response to ``query_logs``.

    Never raises — a logging failure must not degrade the user response.
    """
    try:
        log_entry = QueryLogCreate(
            query_type=f"compliance_chat",
            question=request.question,
            response_text=response.answer,
            latency_ms=int(response.latency_ms),
            model_name=response.model,
            retrieval_payload={
                "collections_searched": response.collections_searched,
                "chunks_used": response.chunks_used,
                "top_k_requested": request.top_k,
                "chunks": [
                    {
                        "chunk_id": c.chunk_id,
                        "collection": c.collection,
                        "score": c.score,
                        "rule_reference": c.rule_reference,
                    }
                    for c in response.retrieved_chunks
                ],
            },
            citation_payload={
                "sources": [s.model_dump() for s in response.sources],
            },
        )
        _query_log_repo.create(session, log_entry)
    except Exception as exc:
        logger.warning("Failed to persist query log: %s", exc)
