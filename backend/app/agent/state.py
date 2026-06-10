"""LangGraph agent state definition for the ADGM compliance workflow.

Architecture
------------
``AgentState`` is the single shared data container that flows through every
node in the LangGraph ``StateGraph``.  Each node receives the full state and
returns a *partial* dict — only the fields it mutates.  LangGraph merges the
partial update back into the state before invoking the next node.

Phase coverage
--------------
* Phase 8  — intent routing, compliance_chat path, capability stubs
* Phase 9  — compliance_review fields populated by review sub-agents
* Phase 10 — clause_generation fields populated by clause generator
* Phase 12 — analytics fields populated by Text2SQL agent
* Phase 11 — similar_cases populated by historical review retriever
"""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from backend.app.schemas.rag import CitationSource, RetrievedChunk

# ── Intent constants ───────────────────────────────────────────────────────────

INTENT_CHAT = "compliance_chat"
INTENT_REVIEW = "compliance_review"
INTENT_CLAUSE = "clause_generation"
INTENT_ANALYTICS = "analytics"

VALID_INTENTS: frozenset[str] = frozenset(
    {INTENT_CHAT, INTENT_REVIEW, INTENT_CLAUSE, INTENT_ANALYTICS}
)


# ── State ──────────────────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """Shared state passed between every node in the compliance workflow graph.

    All fields are optional (``total=False``) so nodes only need to return the
    keys they actually set.  The graph initialises the state with all keys
    before the first node runs, so downstream nodes can always safely read any
    field with a ``.get()`` call.

    Naming convention
    -----------------
    Fields that belong to a single capability are prefixed:
    ``review_*``, ``clause_*``, ``analytics_*``, ``similar_*``.
    Shared fields (question, intent, answer, sources, model) have no prefix.
    """

    # ── Input (set by caller, never mutated by nodes) ──────────────────────────
    question: str
    collections: list[str] | None
    top_k: int

    # ── Routing ────────────────────────────────────────────────────────────────
    intent: str  # one of VALID_INTENTS

    # ── Retrieval (Phase 5-7, compliance_chat + clause_generation) ─────────────
    retrieved_chunks: list[RetrievedChunk]
    collections_searched: list[str]

    # ── Generation (all text-producing capabilities) ──────────────────────────
    answer: str
    sources: list[CitationSource]
    model: str  # "gemini/…" or "groq/…"

    # ── Error propagation ──────────────────────────────────────────────────────
    error: str | None

    # ── Phase 9: Compliance Review (populated by review sub-agents) ────────────
    review_violations: list[dict[str, Any]]
    review_recommendations: list[dict[str, Any]]
    review_score: float | None

    # ── Phase 10: Clause Generation ────────────────────────────────────────────
    clause_text: str

    # ── Phase 11: Similar Cases ────────────────────────────────────────────────
    similar_cases: list[dict[str, Any]]

    # ── Phase 12: Text2SQL Analytics ──────────────────────────────────────────
    analytics_sql: str
    analytics_result: list[dict[str, Any]]


def initial_state(
    question: str,
    collections: list[str] | None,
    top_k: int,
) -> AgentState:
    """Return a fully-initialised ``AgentState`` with safe defaults.

    Passing a fully-populated state to ``graph.invoke()`` prevents KeyError
    in any node that reads a field before it has been set by an upstream node.
    """
    return AgentState(
        question=question,
        collections=collections,
        top_k=top_k,
        intent="",
        retrieved_chunks=[],
        collections_searched=[],
        answer="",
        sources=[],
        model="",
        error=None,
        review_violations=[],
        review_recommendations=[],
        review_score=None,
        clause_text="",
        similar_cases=[],
        analytics_sql="",
        analytics_result=[],
    )
