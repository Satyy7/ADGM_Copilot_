"""LangGraph node functions for the ADGM compliance workflow (Phase 8+).

Each node receives the full ``AgentState`` and returns a *partial* dict
containing only the fields it mutates.  LangGraph merges the partial update
before forwarding state to the next node.

Node inventory
--------------
Phase 8 (this file):
  route_intent          — classify query intent via LLM
  retrieve              — hybrid + re-ranked vector search
  generate              — Gemini/Groq answer generation with citations
  handle_review         — stub (Phase 9)
  handle_clause_gen     — stub (Phase 10)
  handle_analytics      — stub (Phase 12)

Phase 9+:
  Each capability gets its own set of sub-agent nodes added here.

Design: closure factory
-----------------------
``build_nodes(retriever, gemini)`` returns a plain dict mapping node name →
callable.  Nodes are closures that capture their service dependencies — no
global state, no class inheritance.  This makes each node independently
testable by passing mock services to the factory.
"""

from __future__ import annotations

import logging
import re

from backend.app.agent.state import (
    INTENT_ANALYTICS,
    INTENT_CHAT,
    INTENT_CLAUSE,
    INTENT_REVIEW,
    VALID_INTENTS,
    AgentState,
)
from backend.app.schemas.rag import CitationSource, RetrievedChunk
from backend.app.services.retrieval import DEFAULT_RETRIEVAL_COLLECTIONS, Retriever

logger = logging.getLogger(__name__)

# ── Intent classification prompt ───────────────────────────────────────────────

_INTENT_PROMPT: str = """\
Classify the following compliance query into exactly one category.

Categories:
- compliance_chat       : Questions about ADGM regulations, requirements, definitions, procedures, or obligations
- compliance_review     : Requests to review, check, or verify a document (AoA, MoA, employment contract, resolution, etc.)
- clause_generation     : Requests to draft, generate, or create a specific legal clause, contract section, or template
- analytics             : Requests for statistics, counts, trends, or data analysis drawn from compliance records

Query: {question}

Reply with ONLY the category name (e.g. compliance_chat). Nothing else."""

# ── Capability stub responses ──────────────────────────────────────────────────

_STUB_MESSAGES: dict[str, str] = {
    INTENT_REVIEW: (
        "Compliance Document Review (Phase 9) is under development. "
        "Upload your document once this capability is enabled. "
        "For now, use the compliance chat to ask specific regulatory questions."
    ),
    INTENT_CLAUSE: (
        "Clause Generation (Phase 10) is under development. "
        "This capability will draft compliant ADGM clauses with full citations. "
        "For now, use the compliance chat to retrieve template language from the knowledge base."
    ),
    INTENT_ANALYTICS: (
        "Compliance Analytics (Phase 12) is under development. "
        "This capability will translate natural language into SQL queries against "
        "the compliance records database. "
        "For now, use the compliance chat for regulatory Q&A."
    ),
}


# ── Node factory ───────────────────────────────────────────────────────────────

def build_nodes(retriever: Retriever, gemini: object) -> dict[str, object]:
    """Return a mapping of node name → node callable.

    All nodes are closures over ``retriever`` and ``gemini`` so they can be
    unit-tested by passing mocks without touching global state.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object (e.g. ``RerankedRetriever``).
    gemini:
        ``GeminiClient`` instance (type is ``object`` to avoid circular import).
    """

    # ── Node: route_intent ─────────────────────────────────────────────────────

    def route_intent(state: AgentState) -> dict:
        """Classify the question into one of the four compliance intents."""
        question = state["question"]
        prompt = _INTENT_PROMPT.format(question=question)
        intent = INTENT_CHAT  # safe default

        try:
            raw = gemini.generate_text(prompt).strip()  # type: ignore[union-attr]
            # Normalise: lower-case, strip punctuation, take first word/phrase
            cleaned = re.sub(r"[^a-z_]", "", raw.lower().split()[0]) if raw.split() else ""
            if cleaned in VALID_INTENTS:
                intent = cleaned
            else:
                logger.warning(
                    "Unexpected intent '%s' from LLM, defaulting to compliance_chat.", raw
                )
        except Exception as exc:
            logger.warning("Intent routing failed (%s), defaulting to compliance_chat.", exc)

        logger.info("Intent classified as '%s' | question: %.70s…", intent, question)
        return {"intent": intent}

    # ── Node: retrieve ─────────────────────────────────────────────────────────

    def retrieve(state: AgentState) -> dict:
        """Run hybrid + re-ranked retrieval and populate retrieved_chunks."""
        question = state["question"]
        collections = state.get("collections") or list(DEFAULT_RETRIEVAL_COLLECTIONS)
        top_k = state.get("top_k", 5)

        chunks: list[RetrievedChunk] = retriever.search(
            question=question,
            collections=list(collections),
            top_k=top_k,
        )

        logger.info(
            "Retrieved %d chunks from %s.", len(chunks), collections
        )
        return {
            "retrieved_chunks": chunks,
            "collections_searched": list(collections),
        }

    # ── Node: generate ─────────────────────────────────────────────────────────

    def generate(state: AgentState) -> dict:
        """Generate a cited compliance answer from the retrieved chunks."""
        question = state["question"]
        chunks = state.get("retrieved_chunks", [])

        if not chunks:
            return {
                "answer": (
                    "No relevant regulatory context was found. "
                    "Ensure the knowledge base is indexed or rephrase your question."
                ),
                "sources": [],
                "model": "n/a",
            }

        answer: str = gemini.generate_compliance_answer(  # type: ignore[union-attr]
            question=question,
            chunks=chunks,
        )
        sources = _deduplicate_citations(chunks)
        model: str = gemini.active_model  # type: ignore[union-attr]

        logger.info("Generated answer via %s | %d sources.", model, len(sources))
        return {"answer": answer, "sources": sources, "model": model}

    # ── Stub nodes (Phases 9, 10, 12) ─────────────────────────────────────────

    def handle_review(state: AgentState) -> dict:
        return {
            "answer": _STUB_MESSAGES[INTENT_REVIEW],
            "sources": [],
            "model": "n/a",
            "retrieved_chunks": [],
            "collections_searched": [],
        }

    def handle_clause_gen(state: AgentState) -> dict:
        return {
            "answer": _STUB_MESSAGES[INTENT_CLAUSE],
            "sources": [],
            "model": "n/a",
            "retrieved_chunks": [],
            "collections_searched": [],
        }

    def handle_analytics(state: AgentState) -> dict:
        return {
            "answer": _STUB_MESSAGES[INTENT_ANALYTICS],
            "sources": [],
            "model": "n/a",
            "retrieved_chunks": [],
            "collections_searched": [],
        }

    return {
        "route_intent": route_intent,
        "retrieve": retrieve,
        "generate": generate,
        "handle_review": handle_review,
        "handle_clause_gen": handle_clause_gen,
        "handle_analytics": handle_analytics,
    }


# ── Routing function (conditional edge selector) ──────────────────────────────

def select_path(state: AgentState) -> str:
    """Map intent → next node name.

    Called by LangGraph's conditional edge after ``route_intent``.
    Returns the node name string that LangGraph uses to look up the next node.
    """
    intent = state.get("intent", INTENT_CHAT)
    return {
        INTENT_REVIEW:    "handle_review",
        INTENT_CLAUSE:    "handle_clause_gen",
        INTENT_ANALYTICS: "handle_analytics",
    }.get(intent, "retrieve")  # compliance_chat and unknown → retrieve


# ── Citation deduplication (shared by generate node + BaselineRAGPipeline) ────

def _deduplicate_citations(chunks: list[RetrievedChunk]) -> list[CitationSource]:
    seen: set[tuple[str, str, str]] = set()
    citations: list[CitationSource] = []
    for chunk in chunks:
        key = (chunk.source_title or "", chunk.rule_reference or "", chunk.collection)
        if key not in seen:
            seen.add(key)
            citations.append(
                CitationSource(
                    source_title=chunk.source_title or chunk.collection,
                    source_url=chunk.source_url,
                    rule_reference=chunk.rule_reference,
                    collection=chunk.collection,
                    authority=chunk.authority,
                )
            )
    return citations
