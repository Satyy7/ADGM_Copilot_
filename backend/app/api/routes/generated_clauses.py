"""Generated clause API routes — Phase 10.

Endpoints
---------
POST   /generated-clauses/generate   — generate an ADGM-compliant clause (Phase 10)
GET    /generated-clauses            — list persisted clause records (CRUD)
POST   /generated-clauses            — store a clause record manually (CRUD)
GET    /generated-clauses/{id}       — retrieve one clause record (CRUD)
PATCH  /generated-clauses/{id}       — update a clause record (CRUD)
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.agent.clause.graph import get_compiled_clause_graph
from backend.app.api.deps import get_session
from backend.app.api.routes.crud import build_crud_router
from backend.app.models.generated_clause import GeneratedClause
from backend.app.repositories.base import BaseRepository
from backend.app.schemas.clause_result import ClauseRequest, ClauseResult
from backend.app.schemas.generated_clause import (
    GeneratedClauseCreate,
    GeneratedClauseRead,
    GeneratedClauseUpdate,
)

logger = logging.getLogger(__name__)

_clause_repo: BaseRepository = BaseRepository(GeneratedClause)

# ── CRUD router (unchanged from Phase 3) ──────────────────────────────────────

router = build_crud_router(
    model=GeneratedClause,
    create_schema=GeneratedClauseCreate,
    update_schema=GeneratedClauseUpdate,
    read_schema=GeneratedClauseRead,
    prefix="/generated-clauses",
    tags=["Clause Generator"],
)


# ── Phase 10: clause generation endpoint ──────────────────────────────────────

@router.post(
    "/generate",
    response_model=ClauseResult,
    summary="Generate an ADGM-compliant clause",
    description=(
        "Describe the clause you need in plain English. "
        "The system retrieves relevant ADGM regulations and templates, "
        "then drafts a numbered, citation-backed clause ready to insert into your document."
    ),
    tags=["Clause Generator"],
)
def generate_clause(
    request: ClauseRequest,
    session: Session = Depends(get_session),
) -> ClauseResult:
    """Phase 10: parse intent → retrieve regs + templates → LLM legal drafter → cited clause."""
    started_at = time.monotonic()

    try:
        graph = get_compiled_clause_graph()
        final_state: dict = graph.invoke(  # type: ignore[union-attr]
            {
                "request":            request.request,
                "document_type_hint": request.document_type or "",
                "top_k":              request.top_k,
            }
        )
    except Exception as exc:
        logger.error("Clause generation pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clause generation failed: {exc}",
        ) from exc

    latency_ms = round((time.monotonic() - started_at) * 1000, 2)

    clause_text = final_state.get("clause_text", "")
    citations   = final_state.get("citations", [])
    clause_type = final_state.get("clause_type", "general_clause")
    doc_type    = final_state.get("document_type", "general")
    model       = final_state.get("model", "unknown")

    # Persist to DB (fire-and-forget — never fail the response on DB error)
    _persist_clause(
        session=session,
        request=request.request,
        clause_type=clause_type,
        clause_text=clause_text,
        model=model,
        citations=citations,
    )

    return ClauseResult(
        request=request.request,
        clause_type=clause_type,
        document_type=doc_type,
        clause_text=clause_text,
        citations=citations,
        model=model,
        latency_ms=latency_ms,
    )


def _persist_clause(
    session: Session,
    request: str,
    clause_type: str,
    clause_text: str,
    model: str,
    citations: list,
) -> None:
    try:
        _clause_repo.create(
            session,
            GeneratedClauseCreate(
                request_text=request,
                clause_type=clause_type,
                generated_text=clause_text,
                model_name=model,
                citation_payload={"citations": [c.model_dump() for c in citations]},
                validation_status="pending",
            ),
        )
    except Exception as exc:
        logger.error("Failed to persist generated clause: %s", exc, exc_info=True)
