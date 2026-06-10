"""Compliance analytics API route — Phase 12.

Endpoint
--------
POST /analytics/query  — natural language question -> SQL -> execute -> answer

Flow
----
1. LLM converts the question to a SELECT statement (or use ``confirmed_sql``).
2. Static safety validator: SELECT-only, no dangerous keywords, table whitelist.
3. If ``preview_only=True``: return SQL for human review without executing.
4. Execute against PostgreSQL (read-only connection).
5. LLM formats results as a professional compliance narrative.
6. Persist to query_logs for audit trail.

Human-in-the-loop pattern
--------------------------
    # Step 1 — preview
    POST /analytics/query  {"question": "...", "preview_only": true}
    # -> returns generated_sql for review

    # Step 2 — confirm and execute
    POST /analytics/query  {"question": "...", "confirmed_sql": "<reviewed SQL>"}
    # -> executes and returns answer + results
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.agent.analytics.graph import get_compiled_analytics_graph
from backend.app.api.deps import get_session
from backend.app.models.query_log import QueryLog
from backend.app.repositories.base import BaseRepository
from backend.app.schemas.analytics_result import AnalyticsRequest, AnalyticsResult
from backend.app.schemas.query_log import QueryLogCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_query_log_repo: BaseRepository = BaseRepository(QueryLog)


@router.post(
    "/query",
    response_model=AnalyticsResult,
    summary="Run a natural language compliance analytics query",
    description=(
        "Ask a question about your compliance data in plain English. "
        "The system generates a safe SQL query, optionally executes it, and "
        "returns a professional narrative answer with the raw results.\n\n"
        "**Human-approval flow**: set `preview_only=true` to review the generated "
        "SQL before execution, then resubmit with `confirmed_sql` to run it."
    ),
)
def run_analytics_query(
    request: AnalyticsRequest,
    session: Session = Depends(get_session),
) -> AnalyticsResult:
    """Phase 12: question -> SQL -> validate -> execute -> narrative answer."""
    started_at = time.monotonic()

    try:
        graph = get_compiled_analytics_graph()
        final_state: dict = graph.invoke({
            "question":      request.question,
            "preview_only":  request.preview_only,
            "confirmed_sql": request.confirmed_sql or "",
        })
    except Exception as exc:
        logger.error("Analytics pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics pipeline failed: {exc}",
        ) from exc

    latency_ms = round((time.monotonic() - started_at) * 1000, 2)

    generated_sql    = final_state.get("generated_sql", "")
    sql_safe         = bool(final_state.get("sql_safe", False))
    rejection_reason = final_state.get("sql_rejection_reason") or None
    query_results    = final_state.get("query_results", [])
    row_count        = int(final_state.get("row_count", 0))
    columns          = final_state.get("columns", [])
    answer           = final_state.get("answer", "")
    model            = final_state.get("model", "unknown")
    exec_error       = final_state.get("execution_error", "")

    # Persist to query_logs (fire-and-forget)
    _persist_query_log(
        session=session,
        question=request.question,
        generated_sql=generated_sql,
        answer=answer,
        sql_safe=sql_safe,
        sql_executed=sql_safe and not request.preview_only and not exec_error,
        latency_ms=int(latency_ms),
        model=model,
        error=exec_error or rejection_reason,
    )

    return AnalyticsResult(
        question=request.question,
        generated_sql=generated_sql,
        sql_safe=sql_safe,
        sql_rejection_reason=rejection_reason,
        query_results=query_results,
        row_count=row_count,
        columns=columns,
        answer=answer,
        preview_only=request.preview_only,
        model=model,
        latency_ms=latency_ms,
    )


def _persist_query_log(
    session: Session,
    question: str,
    generated_sql: str,
    answer: str,
    sql_safe: bool,
    sql_executed: bool,
    latency_ms: int,
    model: str,
    error: str | None,
) -> None:
    try:
        _query_log_repo.create(
            session,
            QueryLogCreate(
                query_type="analytics",
                question=question,
                response_text=answer,
                generated_sql=generated_sql,
                sql_approved=sql_safe,
                sql_executed=sql_executed,
                latency_ms=latency_ms,
                model_name=model,
                error_message=error,
            ),
        )
    except Exception as exc:
        logger.warning("Failed to persist analytics query log: %s", exc)
