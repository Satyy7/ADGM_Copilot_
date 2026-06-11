"""Six compliance review sub-agent nodes (Phase 9).

Pipeline
--------
classify_document
  → extract_clauses
    → retrieve_regulations
      → detect_violations
        → analyse_gaps
          → generate_report

Each node is a closure over shared ``gemini`` and ``retriever`` service
instances.  ``build_review_nodes(retriever, gemini)`` returns the dict that
``build_review_graph()`` registers with the LangGraph ``StateGraph``.

JSON parsing
------------
Every LLM response is expected to be a JSON array or object.  ``_parse_json``
tries multiple extraction strategies and falls back to an empty structure on
failure so the pipeline never hard-crashes on a bad LLM response.

Score calculation
-----------------
The compliance score is computed deterministically from violation and gap
counts rather than letting the LLM calculate it — LLMs are unreliable at
arithmetic.  See ``_calculate_score``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.agent.review.prompts import (
    ANALYSE_GAPS_PROMPT,
    CLASSIFY_PROMPT,
    DETECT_VIOLATIONS_PROMPT,
    EXTRACT_CLAUSES_PROMPT,
    GENERATE_SUMMARY_PROMPT,
)
from backend.app.services.retrieval import DEFAULT_RETRIEVAL_COLLECTIONS, Retriever

logger = logging.getLogger(__name__)

# Collections searched for regulation evidence
_REVIEW_COLLECTIONS = ["regulations", "guidance", "checklists"]
_REGULATION_CANDIDATES = 10   # chunks retrieved for regulation context


def build_review_nodes(retriever: Retriever, gemini: object) -> dict[str, Any]:
    """Return a mapping of node name → callable for the review sub-graph.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object (e.g. ``RerankedRetriever``).
    gemini:
        ``GeminiClient`` instance (typed as ``object`` to avoid circular imports).
    """

    # ── 1. Classify document ──────────────────────────────────────────────────

    def classify_document(state: dict) -> dict:
        text = state.get("document_text", "")
        prompt = CLASSIFY_PROMPT.format(text=text[:1500])
        try:
            raw = gemini.generate_text(prompt).strip().lower()  # type: ignore[union-attr]
            # Normalise: keep only identifier characters
            doc_type = re.sub(r"[^a-z_]", "", raw.split()[0]) if raw.split() else "other"
        except Exception as exc:
            logger.warning("classify_document failed (%s), defaulting to 'other'.", exc)
            doc_type = "other"

        logger.info("Document classified as '%s'.", doc_type)
        return {"document_type": doc_type}

    # ── 2. Extract clauses ────────────────────────────────────────────────────

    def extract_clauses(state: dict) -> dict:
        text = state.get("document_text", "")
        doc_type = state.get("document_type", "document")
        prompt = EXTRACT_CLAUSES_PROMPT.format(document_type=doc_type, text=text[:6000])
        try:
            raw = gemini.generate_text(prompt)  # type: ignore[union-attr]
            clauses = _parse_json_array(raw)
        except Exception as exc:
            logger.warning("extract_clauses failed (%s), using empty list.", exc)
            clauses = []

        logger.info("Extracted %d clauses.", len(clauses))
        return {"extracted_clauses": clauses}

    # ── 3. Retrieve regulations ────────────────────────────────────────────────

    def retrieve_regulations(state: dict) -> dict:
        doc_type = state.get("document_type", "document")
        clauses = state.get("extracted_clauses", [])

        # Build a single retrieval query from document type + clause categories
        clause_sample = " ".join(
            c.get("text", "")[:80] for c in clauses[:5]
        )
        query = f"{doc_type} compliance requirements {clause_sample}"

        try:
            hits = retriever.search(
                question=query,
                collections=_REVIEW_COLLECTIONS,
                top_k=_REGULATION_CANDIDATES,
            )
            regulations = [
                {
                    "text": h.text,
                    "source_title": h.source_title or "",
                    "rule_reference": h.rule_reference or "",
                    "collection": h.collection,
                }
                for h in hits
            ]
        except Exception as exc:
            logger.warning("retrieve_regulations failed (%s), using empty list.", exc)
            regulations = []

        logger.info("Retrieved %d regulation chunks for review context.", len(regulations))
        return {"retrieved_regulations": regulations}

    # ── 4. Detect violations ──────────────────────────────────────────────────

    def detect_violations(state: dict) -> dict:
        doc_type = state.get("document_type", "document")
        clauses = state.get("extracted_clauses", [])
        regulations = state.get("retrieved_regulations", [])

        if not clauses:
            return {"violations": []}

        regs_text = "\n".join(
            f"[{r['source_title']}] {r['text'][:300]}" for r in regulations
        )
        clauses_text = "\n".join(
            f"- {c.get('heading', 'Clause')}: {c.get('text', '')[:250]}"
            for c in clauses
        )
        prompt = DETECT_VIOLATIONS_PROMPT.format(
            document_type=doc_type,
            regulations=regs_text or "No regulations retrieved.",
            clauses=clauses_text,
        )
        try:
            raw = gemini.generate_text(prompt)  # type: ignore[union-attr]
            violations = _parse_json_array(raw)
        except Exception as exc:
            logger.warning("detect_violations failed (%s), using empty list.", exc)
            violations = []

        logger.info("Detected %d violation(s).", len(violations))
        return {"violations": violations}

    # ── 5. Analyse gaps ───────────────────────────────────────────────────────

    def analyse_gaps(state: dict) -> dict:
        doc_type = state.get("document_type", "document")
        clauses = state.get("extracted_clauses", [])

        clause_headings = "\n".join(
            f"- {c.get('heading', 'Unnamed')}" for c in clauses
        ) or "No clauses extracted."

        prompt = ANALYSE_GAPS_PROMPT.format(
            document_type=doc_type,
            clause_headings=clause_headings,
        )
        try:
            raw = gemini.generate_text(prompt)  # type: ignore[union-attr]
            gaps = _parse_json_array(raw)
        except Exception as exc:
            logger.warning("analyse_gaps failed (%s), using empty list.", exc)
            gaps = []

        logger.info("Identified %d gap(s).", len(gaps))
        return {"gaps": gaps}

    # ── 6. Generate report ────────────────────────────────────────────────────

    def generate_report(state: dict) -> dict:
        doc_type = state.get("document_type", "document")
        violations = state.get("violations", [])
        gaps = state.get("gaps", [])

        score = _calculate_score(violations, gaps)

        violations_brief = "; ".join(v.get("title", "issue") for v in violations[:3]) or "none"
        gaps_brief = "; ".join(g.get("missing_provision", "gap") for g in gaps[:3]) or "none"

        prompt = GENERATE_SUMMARY_PROMPT.format(
            document_type=doc_type,
            violation_count=len(violations),
            violations_brief=violations_brief,
            gap_count=len(gaps),
            gaps_brief=gaps_brief,
        )
        try:
            summary = gemini.generate_text(prompt).strip()  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("generate_report summary failed (%s).", exc)
            summary = (
                f"Review of {doc_type} complete. "
                f"Found {len(violations)} violation(s) and {len(gaps)} gap(s). "
                f"Compliance score: {score:.0f}/100."
            )

        model: str = getattr(gemini, "active_model", "unknown")  # type: ignore[union-attr]
        logger.info("Report generated — score=%.1f violations=%d gaps=%d", score, len(violations), len(gaps))
        return {"compliance_score": score, "summary": summary, "model": model}

    return {
        "classify_document":   classify_document,
        "extract_clauses":     extract_clauses,
        "retrieve_regulations": retrieve_regulations,
        "detect_violations":   detect_violations,
        "analyse_gaps":        analyse_gaps,
        "generate_report":     generate_report,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_array(raw: str) -> list[dict]:
    """Parse an LLM response expected to be a JSON array.

    Tries three strategies:
    1. Direct ``json.loads`` of the whole response.
    2. Extract the first ``[...]`` block via regex.
    3. Return ``[]`` on complete failure.
    """
    text = raw.strip()
    # Strategy 1: whole response is valid JSON
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: find the JSON array block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON array from LLM response: %.100s…", text)
    return []


_VIOLATION_DEDUCTIONS = {"high": 15, "medium": 7, "low": 3}
_GAP_DEDUCTIONS       = {"high": 10, "medium": 5, "low": 2}


def _calculate_score(violations: list[dict], gaps: list[dict]) -> float:
    """Compute a deterministic compliance score from 0–100.

    Start at 100 and deduct per-issue amounts based on severity.
    Using a deterministic calculation is more reliable than asking the LLM.
    """
    score = 100.0
    for v in violations:
        score -= _VIOLATION_DEDUCTIONS.get(v.get("severity", "low"), 3)
    for g in gaps:
        score -= _GAP_DEDUCTIONS.get(g.get("severity", "low"), 2)
    return round(max(0.0, score), 1)
