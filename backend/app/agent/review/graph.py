"""LangGraph compliance review sub-graph (Phase 9).

Graph topology
--------------
    START
      │
      ▼
  classify_document       (LLM: identify doc type)
      │
      ▼
  extract_clauses         (LLM: pull key clauses as JSON)
      │
      ▼
  retrieve_regulations    (Retriever: fetch relevant ADGM regulations)
      │
      ▼
  detect_violations       (LLM: compare clauses vs regulations → violations JSON)
      │
      ▼
  analyse_gaps            (LLM: identify missing mandatory provisions → gaps JSON)
      │
      ▼
  generate_report         (LLM: executive summary + deterministic score)
      │
      ▼
    END

This sub-graph is a pure sequential pipeline — each agent needs the full
output of all previous agents.  Parallelisation (e.g. running
``detect_violations`` and ``analyse_gaps`` concurrently) is planned for
Phase 14 (CRAG optimisation round).

State
-----
``ReviewState`` is a standalone TypedDict — separate from the main
``AgentState`` so the review pipeline can be tested and invoked independently
of the intent router.

Usage
-----
    from backend.app.agent.review.graph import get_compiled_review_graph

    graph = get_compiled_review_graph()
    result = graph.invoke({
        "document_text": "...",
        "document_name": "my_aoa.pdf",
    })
    # result is a populated ReviewState dict
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from backend.app.agent.review.nodes import build_review_nodes
from backend.app.core.config import get_settings
from backend.app.db.qdrant import get_qdrant_client
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.embeddings import get_embeddings_service
from backend.app.services.generation import GeminiClient
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.reranker import LLMReranker, RerankedRetriever
from backend.app.services.retrieval import QdrantRetriever

logger = logging.getLogger(__name__)


# ── Review-specific state ──────────────────────────────────────────────────────

class ReviewState(TypedDict, total=False):
    """State flowing through the six-node compliance review pipeline."""

    # Input (provided by caller)
    document_text: str
    document_name: str

    # Set by classify_document
    document_type: str

    # Set by extract_clauses
    extracted_clauses: list[dict[str, Any]]

    # Set by retrieve_regulations
    retrieved_regulations: list[dict[str, Any]]

    # Set by detect_violations
    violations: list[dict[str, Any]]

    # Set by analyse_gaps
    gaps: list[dict[str, Any]]

    # Set by generate_report
    compliance_score: float
    summary: str
    model: str


# ── Graph factory ──────────────────────────────────────────────────────────────

def build_review_graph(retriever: object, gemini: GeminiClient) -> object:
    """Build and compile the six-node compliance review sub-graph.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object.
    gemini:
        ``GeminiClient`` instance shared across all six nodes.
    """
    nodes = build_review_nodes(retriever=retriever, gemini=gemini)  # type: ignore[arg-type]

    graph: StateGraph = StateGraph(ReviewState)
    for name, fn in nodes.items():
        graph.add_node(name, fn)

    graph.add_edge(START,                  "classify_document")
    graph.add_edge("classify_document",    "extract_clauses")
    graph.add_edge("extract_clauses",      "retrieve_regulations")
    graph.add_edge("retrieve_regulations", "detect_violations")
    graph.add_edge("detect_violations",    "analyse_gaps")
    graph.add_edge("analyse_gaps",         "generate_report")
    graph.add_edge("generate_report",      END)

    compiled = graph.compile()
    logger.info("Compliance review sub-graph compiled.")
    return compiled


@lru_cache(maxsize=1)
def get_compiled_review_graph() -> object:
    """Build and cache the review graph with its full retrieval stack.

    Call ``get_compiled_review_graph.cache_clear()`` in tests.
    """
    settings = get_settings()
    embeddings = get_embeddings_service(settings=settings)
    qdrant = get_qdrant_client()

    dense    = QdrantRetriever(qdrant_client=qdrant, embeddings_service=embeddings)
    sparse   = BM25Retriever()
    hybrid   = HybridRetriever(dense=dense, sparse=sparse)
    gemini   = GeminiClient(settings=settings)
    reranker = LLMReranker(client=gemini)
    retriever = RerankedRetriever(base=hybrid, reranker=reranker, candidate_pool=10)

    return build_review_graph(retriever=retriever, gemini=gemini)
