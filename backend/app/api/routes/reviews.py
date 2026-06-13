"""Compliance review API routes — Phase 9.

Endpoints
---------
POST   /reviews/analyze      — upload a PDF/DOCX, run the 6-agent review pipeline
GET    /reviews               — list persisted review records
POST   /reviews               — create a review record manually
GET    /reviews/{id}          — get one review record
PATCH  /reviews/{id}          — update a review record

The ``/analyze`` endpoint is the primary Phase 9 feature.  It accepts a
document upload, runs it through the LangGraph review sub-graph, and returns
a structured ``ReviewReport`` without requiring a prior ``document_id``.

The CRUD endpoints below it persist review records created by the legacy
workflow or manual QA workflows.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.agent.cases.indexer import get_indexer
from backend.app.agent.cases.retriever import get_retriever
from backend.app.agent.review.graph import get_compiled_review_graph
from backend.app.api.deps import get_session
from backend.app.api.routes.crud import build_crud_router
from backend.app.models.document import Document as DocumentModel
from backend.app.models.recommendation import Recommendation as RecommendationModel
from backend.app.models.review import Review
from backend.app.models.violation import Violation as ViolationModel
from backend.app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate
from backend.app.schemas.review_report import (
    DetectedViolation,
    Recommendation,
    ReviewReport,
)
from backend.app.services.document_extractor import extract_text

logger = logging.getLogger(__name__)

# ── CRUD router (unchanged from Phase 3) ──────────────────────────────────────

router = build_crud_router(
    model=Review,
    create_schema=ReviewCreate,
    update_schema=ReviewUpdate,
    read_schema=ReviewRead,
    prefix="/reviews",
    tags=["Compliance Review"],
)

# ── Phase 9: document analysis endpoint ───────────────────────────────────────

_ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",   # some browsers send this for .docx
}
_ALLOWED_EXT = {".pdf", ".docx", ".doc"}


@router.post(
    "/analyze",
    response_model=ReviewReport,
    summary="Analyze a document for ADGM compliance",
    description=(
        "Upload a PDF or DOCX document (AoA, MoA, employment contract, UBO declaration, etc.). "
        "The system runs a 6-agent AI pipeline to classify the document, extract clauses, "
        "map them to ADGM regulations, detect violations, identify gaps, and produce a "
        "scored compliance report."
    ),
    tags=["Compliance Review"],
)
async def analyze_document(
    file: UploadFile = File(..., description="PDF or DOCX document to review"),
    session: Session = Depends(get_session),
) -> ReviewReport:
    """Phase 9: 6-agent compliance review — classify → extract → retrieve → detect → gap → report."""
    started_at = time.monotonic()

    # ── Validate file type ─────────────────────────────────────────────────────
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Upload a .pdf or .docx file.",
        )

    # ── Extract text ───────────────────────────────────────────────────────────
    try:
        content = await file.read()
        document_text = extract_text(content, filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error("Document extraction failed for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not extract text from document: {exc}",
        ) from exc

    if not document_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted document text is empty. Ensure the file is not scanned-image-only.",
        )

    # ── Run 6-agent review pipeline ────────────────────────────────────────────
    try:
        graph = get_compiled_review_graph()
        final_state: dict = graph.invoke(  # type: ignore[union-attr]
            {
                "document_text": document_text,
                "document_name": filename,
            }
        )
    except Exception as exc:
        logger.error("Review pipeline failed for '%s': %s", filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review pipeline failed: {exc}",
        ) from exc

    latency_ms = round((time.monotonic() - started_at) * 1000, 2)

    # ── Build report ────────────────────────────────────────────────────────────
    raw_violations = final_state.get("violations", [])
    raw_gaps       = final_state.get("gaps", [])

    violations      = [_coerce_violation(v)       for v in raw_violations if isinstance(v, dict)]
    recommendations = [_coerce_recommendation(g)  for g in raw_gaps       if isinstance(g, dict)]

    report = ReviewReport(
        document_name=filename,
        document_type=final_state.get("document_type", "unknown"),
        compliance_score=final_state.get("compliance_score", 0.0),
        summary=final_state.get("summary", ""),
        violations=violations,
        recommendations=recommendations,
        model=final_state.get("model", "unknown"),
        latency_ms=latency_ms,
    )

    # ── Phase 11: retrieve similar historical cases ────────────────────────────
    similar_cases = _find_similar_cases(report)
    report = report.model_copy(update={"similar_cases": similar_cases})

    # ── Phase 11: index this review for future similarity searches ────────────
    _index_review(report)

    # ── Persist document + review + violations + recommendations to PostgreSQL ─
    _persist_review(
        session=session,
        filename=filename,
        ext=ext,
        mime_type=file.content_type,
        report=report,
    )

    return report


# ── Schema coercers ────────────────────────────────────────────────────────────

def _coerce_violation(v: dict) -> DetectedViolation:
    """Coerce a raw LLM dict into a ``DetectedViolation``, filling missing keys."""
    heading = v.get("clause_heading", "Unknown clause")
    return DetectedViolation(
        clause_heading=heading,
        clause_reference=heading or None,
        clause_excerpt=v.get("clause_excerpt", ""),
        violation_type=v.get("violation_type", "non_compliant_clause"),
        severity=v.get("severity", "medium"),
        title=v.get("title", "Compliance issue"),
        description=v.get("description", ""),
        regulation_reference=v.get("regulation_reference"),
        recommendation=v.get("recommendation", ""),
    )


def _coerce_recommendation(g: dict) -> Recommendation:
    """Convert a raw LLM gap dict into a ``Recommendation`` for the frontend."""
    provision = g.get("missing_provision", "Missing provision")
    reg_ref   = g.get("regulation_reference")
    severity  = g.get("severity", "medium")
    action    = g.get("recommendation", "")

    description = "This required provision is absent from the document."
    if reg_ref:
        description = f"Required by {reg_ref}. This provision is absent from the document."

    return Recommendation(
        title=provision,
        description=description,
        priority=severity,
        action_required=action or None,
    )


# ── Phase 11 helpers ───────────────────────────────────────────────────────────

def _find_similar_cases(report: ReviewReport) -> list:
    """Retrieve similar historical cases — never raises, returns [] on failure."""
    try:
        query_parts = [report.document_type]
        if report.violations:
            query_parts.extend(v.title for v in report.violations[:3])
        query = " ".join(query_parts)
        return get_retriever().search(query=query, top_k=3)
    except Exception as exc:
        logger.warning("Similar-case retrieval failed: %s", exc)
        return []


def _index_review(report: ReviewReport) -> None:
    """Index the completed review into historical_reviews — never raises."""
    try:
        get_indexer().index(report)
    except Exception as exc:
        logger.warning("Review indexing failed: %s", exc)


def _persist_review(
    session: Session,
    filename: str,
    ext: str,
    mime_type: str | None,
    report: ReviewReport,
) -> None:
    """Write document → review → violations → recommendations in one transaction.

    Never raises — a DB failure must not degrade the review response returned
    to the user.  Errors are logged at ERROR level with full traceback.
    """
    try:
        now = datetime.now(timezone.utc)

        # 1 — Document record
        doc = DocumentModel(
            original_filename=filename,
            file_extension=ext,
            mime_type=mime_type or "application/octet-stream",
            extraction_status="completed",
            detected_document_type=report.document_type or None,
        )
        session.add(doc)
        session.flush()  # assigns doc.id without committing

        # 2 — Review record
        rev = Review(
            document_id=doc.id,
            review_type=report.document_type or "general_review",
            status="completed",
            compliance_score=Decimal(str(round(report.compliance_score, 2))),
            summary=report.summary or None,
            started_at=now,
            completed_at=now,
            report_payload={
                "model": report.model,
                "latency_ms": report.latency_ms,
                "violation_count": len(report.violations),
                "recommendation_count": len(report.recommendations),
            },
        )
        session.add(rev)
        session.flush()  # assigns rev.id

        # 3 — Violations
        for v in report.violations:
            session.add(ViolationModel(
                review_id=rev.id,
                violation_type=v.violation_type or "non_compliant_clause",
                severity=v.severity or "medium",
                title=(v.title or "Compliance issue")[:300],
                description=v.description or "",
                regulation_reference=(v.regulation_reference or "")[:300] or None,
                document_excerpt=v.clause_excerpt or None,
                status="open",
            ))

        # 4 — Recommendations (from gaps)
        for r in report.recommendations:
            rec_text = r.description or r.title
            if r.action_required:
                rec_text = f"{rec_text}\n\nAction required: {r.action_required}"
            session.add(RecommendationModel(
                review_id=rev.id,
                title=(r.title or "Recommendation")[:300],
                recommendation_text=rec_text or r.title,
                priority=r.priority or "medium",
                status="open",
            ))

        session.commit()
        logger.info(
            "Persisted review for '%s' — doc=%s  review=%s  violations=%d  recommendations=%d",
            filename, doc.id, rev.id,
            len(report.violations), len(report.recommendations),
        )

    except Exception as exc:
        logger.error(
            "Failed to persist review for '%s': %s", filename, exc, exc_info=True
        )
        try:
            session.rollback()
        except Exception:
            pass
