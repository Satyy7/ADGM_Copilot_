"""Self-RAG nodes — Phase 15.

Self-RAG adds two self-reflection checkpoints to the compliance_chat path:

1. self_check_evidence  (before generation)
   Evaluates whether the retrieved regulatory chunks contain *enough* specific
   information to answer the question confidently.  Sets ``evidence_sufficiency``
   in state.  If INSUFFICIENT, the generate node is still called, but the
   subsequent grounding check is more likely to catch a hallucinated answer.

2. self_grade_answer  (after generation)
   Evaluates whether the generated answer is *grounded* in the retrieved
   evidence — i.e. every material claim is supported by or consistent with the
   retrieved chunks.  If the answer is UNGROUNDED, it is replaced with a
   conservative response that acknowledges the limitation and directs the user
   to official ADGM sources rather than risking a false compliance statement.

Why both checks?
----------------
``self_check_evidence`` is a *leading* indicator: it flags low-quality retrieval
before any generation cost is incurred, enabling future phases to short-circuit
generation entirely.

``self_grade_answer`` is a *lagging* guard: it catches cases where the LLM
extrapolated beyond the retrieved evidence — the most dangerous failure mode for
a compliance platform where a hallucinated regulation reference could lead to a
real legal error.

Graph position (Phase 15)
--------------------------
    retrieve
        → crag_evaluate
            → self_check_evidence   (Phase 15 — this file)
                → generate
                    → self_grade_answer   (Phase 15 — this file)
                        → END
    (rewrite_and_retrieve → self_check_evidence on the irrelevant path)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Prompts ────────────────────────────────────────────────────────────────────

_EVIDENCE_CHECK_PROMPT = """\
You are evaluating whether retrieved regulatory documents contain enough \
specific information to confidently answer a compliance question.

Question: {question}

Retrieved regulatory context:
{context}

Does the context contain SPECIFIC regulatory requirements, obligations, \
thresholds, timeframes, or procedures that directly address this question?

Reply with EXACTLY one word:
SUFFICIENT   — the context has specific information to answer the question
INSUFFICIENT — the context lacks the specific information needed

Answer:"""

_GROUNDING_CHECK_PROMPT = """\
You are a compliance accuracy auditor. Verify whether the generated answer \
is supported by the retrieved regulatory evidence.

Question: {question}

Retrieved evidence:
{context}

Generated answer:
{answer}

Is every material claim in the answer directly supported by or consistent \
with the retrieved evidence above?

Reply with EXACTLY one word:
GROUNDED   — all key claims are supported by the evidence
UNGROUNDED — the answer contains claims not found in or contradicted by the evidence

Answer:"""

# ── Grade constants ────────────────────────────────────────────────────────────

EVIDENCE_SUFFICIENT   = "sufficient"
EVIDENCE_INSUFFICIENT = "insufficient"
ANSWER_GROUNDED       = "grounded"
ANSWER_UNGROUNDED     = "ungrounded"

_CONSERVATIVE_ANSWER = (
    "The retrieved regulatory context does not contain sufficient information "
    "to provide a fully grounded answer to this question. "
    "Please consult the official ADGM regulatory documentation or an "
    "ADGM-accredited compliance professional for authoritative guidance on this matter."
)


# ── Node factory ───────────────────────────────────────────────────────────────

def build_self_rag_nodes(gemini: object) -> dict[str, Any]:
    """Return Self-RAG node callables keyed by node name.

    Parameters
    ----------
    gemini:
        ``GeminiClient`` instance shared across the whole graph.
    """

    # ── Node 1: self_check_evidence ────────────────────────────────────────────

    def self_check_evidence(state: dict) -> dict:
        """Evaluate whether retrieved evidence is sufficient to answer the question.

        Uses the rewritten query if CRAG rewrote it, otherwise the original.
        Defaults to SUFFICIENT on any failure — never blocks generation.
        """
        question = state.get("rewritten_query") or state.get("question", "")
        chunks   = state.get("retrieved_chunks", [])

        if not chunks:
            logger.info("Self-RAG evidence check: INSUFFICIENT (no chunks).")
            return {"evidence_sufficiency": EVIDENCE_INSUFFICIENT}

        sample  = chunks[:4]
        context = "\n".join(
            f"[{i + 1}] {c.text[:200].strip()}" for i, c in enumerate(sample)
        )
        prompt = _EVIDENCE_CHECK_PROMPT.format(question=question, context=context)

        sufficiency = EVIDENCE_SUFFICIENT   # safe default
        try:
            raw = gemini.generate_text(prompt).strip().upper()  # type: ignore[union-attr]
            first = re.sub(r"[^A-Z]", "", raw.split()[0]) if raw.split() else ""
            if first == "INSUFFICIENT":
                sufficiency = EVIDENCE_INSUFFICIENT
            else:
                sufficiency = EVIDENCE_SUFFICIENT
        except Exception as exc:
            logger.warning(
                "Self-RAG evidence check failed (%s) — defaulting to SUFFICIENT.", exc
            )

        logger.info(
            "Self-RAG evidence: %s | chunks=%d | question=%.60s…",
            sufficiency.upper(), len(chunks), question,
        )
        return {"evidence_sufficiency": sufficiency}

    # ── Node 2: self_grade_answer ──────────────────────────────────────────────

    def self_grade_answer(state: dict) -> dict:
        """Grade the generated answer for grounding in retrieved evidence.

        If UNGROUNDED, replaces the answer with a conservative disclaimer
        to prevent false compliance guidance from reaching the user.
        Defaults to GROUNDED on any failure — never discards a valid answer.
        """
        question = state.get("question", "")
        answer   = state.get("answer",   "")
        chunks   = state.get("retrieved_chunks", [])

        # Skip grading when there is nothing to grade
        if not answer or not chunks:
            logger.info("Self-RAG grounding check skipped (no answer or no chunks).")
            return {"answer_grade": ANSWER_GROUNDED}

        # Also skip grading the built-in "no context" fallback messages
        if "No relevant regulatory context was found" in answer:
            return {"answer_grade": ANSWER_GROUNDED}

        sample  = chunks[:3]
        context = "\n".join(
            f"[{i + 1}] {c.text[:220].strip()}" for i, c in enumerate(sample)
        )
        prompt = _GROUNDING_CHECK_PROMPT.format(
            question=question,
            context=context,
            answer=answer[:700],
        )

        grade = ANSWER_GROUNDED   # safe default
        try:
            raw   = gemini.generate_text(prompt).strip().upper()  # type: ignore[union-attr]
            first = re.sub(r"[^A-Z]", "", raw.split()[0]) if raw.split() else ""
            if first == "UNGROUNDED":
                grade = ANSWER_UNGROUNDED
            else:
                grade = ANSWER_GROUNDED
        except Exception as exc:
            logger.warning(
                "Self-RAG grounding check failed (%s) — defaulting to GROUNDED.", exc
            )

        logger.info("Self-RAG answer grade: %s", grade.upper())

        if grade == ANSWER_UNGROUNDED:
            logger.warning(
                "Self-RAG: answer is UNGROUNDED — replacing with conservative response."
            )
            return {
                "answer_grade": grade,
                "answer":       _CONSERVATIVE_ANSWER,
            }

        return {"answer_grade": grade}

    return {
        "self_check_evidence": self_check_evidence,
        "self_grade_answer":   self_grade_answer,
    }
