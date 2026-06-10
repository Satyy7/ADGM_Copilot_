"""CRAG (Corrective Retrieval-Augmented Generation) nodes — Phase 14.

CRAG inserts a retrieval-quality gate between the retrieve and generate
nodes.  If the retrieved chunks are off-topic, the query is rewritten and
retrieval is retried before generation proceeds.

Grading rubric
--------------
RELEVANT   — retrieved chunks directly address the question → generate
IRRELEVANT — chunks are off-topic → rewrite query → re-retrieve → generate
AMBIGUOUS  — chunks partially relevant → generate with what we have

Two-node design
---------------
crag_evaluate
    LLM grades the top-3 retrieved chunks against the question.
    Sets ``retrieval_grade`` in state.

rewrite_and_retrieve
    Called only when grade == "irrelevant".
    LLM rewrites the query with better ADGM regulatory vocabulary.
    Re-runs retrieval with the new query.
    Updates ``retrieved_chunks``, ``rewritten_query`` in state.

Routing
-------
``select_crag_path(state)`` is the conditional-edge function used by
``graph.py`` after ``crag_evaluate``:
    "relevant"  | "ambiguous"  → "generate"
    "irrelevant"               → "rewrite_and_retrieve"
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.app.schemas.rag import RetrievedChunk
from backend.app.services.retrieval import DEFAULT_RETRIEVAL_COLLECTIONS, Retriever

logger = logging.getLogger(__name__)

# ── Prompts ────────────────────────────────────────────────────────────────────

_EVAL_PROMPT = """\
You are a retrieval quality evaluator for an ADGM compliance knowledge base.

User question:
{question}

Top retrieved document excerpts:
{context}

Do these documents contain information that would help answer the question?

Reply with EXACTLY one word:
RELEVANT   — documents directly address the question
IRRELEVANT — documents are off-topic or do not address this question
AMBIGUOUS  — documents are only partially relevant

Answer:"""

_REWRITE_PROMPT = """\
The following compliance question returned poorly-matched results from the \
ADGM regulatory knowledge base. Rewrite it to improve retrieval.

Rewriting guidelines:
- Use formal ADGM regulatory terminology
  (e.g. "beneficial owner" not "UBO", "Articles of Association" not "AoA")
- Name the relevant regulation if known
  (e.g. "ADGM Companies Regulations 2020", "ADGM Employment Regulations 2019")
- Focus on the specific compliance obligation, threshold, or procedure
- Be concise — one sentence only

Original question: {question}

Improved retrieval query (one sentence):"""

# ── Grade constants ────────────────────────────────────────────────────────────

GRADE_RELEVANT   = "relevant"
GRADE_IRRELEVANT = "irrelevant"
GRADE_AMBIGUOUS  = "ambiguous"


# ── Node factory ───────────────────────────────────────────────────────────────

def build_crag_nodes(retriever: Retriever, gemini: object) -> dict[str, Any]:
    """Return CRAG node callables keyed by node name.

    Parameters
    ----------
    retriever:
        The full retrieval stack (HyDE → RerankedRetriever → Hybrid → …).
        Used by ``rewrite_and_retrieve`` to re-run search.
    gemini:
        ``GeminiClient`` instance for evaluation and query rewriting.
    """

    # ── Node: crag_evaluate ────────────────────────────────────────────────────

    def crag_evaluate(state: dict) -> dict:
        """Grade retrieved chunks as relevant / irrelevant / ambiguous."""
        question = state.get("question", "")
        chunks: list[RetrievedChunk] = state.get("retrieved_chunks", [])

        if not chunks:
            logger.info("CRAG: no chunks retrieved — grading as IRRELEVANT.")
            return {"retrieval_grade": GRADE_IRRELEVANT}

        # Sample the top-3 chunks to keep the evaluation prompt short
        sample = chunks[:3]
        context = "\n".join(
            f"[{i + 1}] {c.text[:220].strip()}"
            for i, c in enumerate(sample)
        )

        prompt = _EVAL_PROMPT.format(question=question, context=context)

        grade = GRADE_AMBIGUOUS  # safe default
        try:
            raw = gemini.generate_text(prompt).strip().upper()  # type: ignore[union-attr]
            # Extract the grade word from the first non-empty line
            first_word = re.sub(r"[^A-Z]", "", raw.split()[0]) if raw.split() else ""
            if first_word == "RELEVANT":
                grade = GRADE_RELEVANT
            elif first_word == "IRRELEVANT":
                grade = GRADE_IRRELEVANT
            else:
                grade = GRADE_AMBIGUOUS
        except Exception as exc:
            logger.warning("CRAG evaluation failed (%s) — defaulting to AMBIGUOUS.", exc)

        logger.info(
            "CRAG grade: %s | question=%.70s…  chunks=%d",
            grade.upper(), question, len(chunks),
        )
        return {"retrieval_grade": grade}

    # ── Node: rewrite_and_retrieve ─────────────────────────────────────────────

    def rewrite_and_retrieve(state: dict) -> dict:
        """Rewrite the query and re-run retrieval with better terminology."""
        question = state.get("question", "")

        # Step 1 — rewrite the query
        rewritten = question  # fallback
        try:
            prompt = _REWRITE_PROMPT.format(question=question)
            rewritten = gemini.generate_text(prompt).strip()  # type: ignore[union-attr]
            # Strip leading quotation marks the LLM sometimes adds
            rewritten = rewritten.strip('"\'')
            if not rewritten:
                rewritten = question
        except Exception as exc:
            logger.warning("CRAG query rewrite failed (%s) — using original.", exc)

        logger.info(
            "CRAG rewrite: '%s' → '%s'",
            question[:60], rewritten[:60],
        )

        # Step 2 — re-retrieve with the rewritten query
        collections = state.get("collections") or list(DEFAULT_RETRIEVAL_COLLECTIONS)
        top_k = state.get("top_k", 5)

        try:
            new_chunks: list[RetrievedChunk] = retriever.search(
                question=rewritten,
                collections=list(collections),
                top_k=top_k,
            )
        except Exception as exc:
            logger.warning("CRAG re-retrieval failed (%s) — keeping original chunks.", exc)
            new_chunks = state.get("retrieved_chunks", [])

        logger.info(
            "CRAG re-retrieval: %d chunks for rewritten query.", len(new_chunks)
        )
        return {
            "rewritten_query": rewritten,
            "retrieved_chunks": new_chunks,
            "collections_searched": list(collections),
        }

    return {
        "crag_evaluate":        crag_evaluate,
        "rewrite_and_retrieve": rewrite_and_retrieve,
    }


# ── Routing function ───────────────────────────────────────────────────────────

def select_crag_path(state: dict) -> str:
    """Conditional edge selector after ``crag_evaluate``.

    Returns the name of the next node for LangGraph to route to.
    """
    grade = state.get("retrieval_grade", GRADE_AMBIGUOUS)
    if grade == GRADE_IRRELEVANT:
        logger.info("CRAG routing to rewrite_and_retrieve (grade=IRRELEVANT).")
        return "rewrite_and_retrieve"
    logger.info("CRAG routing to generate (grade=%s).", grade)
    return "generate"
