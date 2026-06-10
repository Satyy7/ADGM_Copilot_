"""LangGraph clause generator sub-graph (Phase 10).

Graph topology
--------------
    START
      │
      ▼
  parse_request       (LLM: extract clause_type, document_type, key_requirements)
      │
      ▼
  retrieve_context    (Retriever: regulations + templates → top-K chunks)
      │
      ▼
  generate_clause     (LLM: legal-drafter persona → numbered, cited clause)
      │
      ▼
    END

State
-----
``ClauseState`` is a standalone TypedDict independent of the main ``AgentState``
so the clause pipeline can be invoked directly from the API endpoint OR from
the main graph's ``handle_clause_gen`` node.

Usage
-----
    from backend.app.agent.clause.graph import get_compiled_clause_graph

    graph = get_compiled_clause_graph()
    result = graph.invoke({
        "request": "Draft a UBO disclosure clause for an ADGM private company.",
        "document_type_hint": "articles_of_association",
        "top_k": 8,
    })
    # result["clause_text"] contains the drafted clause
    # result["citations"]   contains CitationSource objects
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from backend.app.agent.clause.nodes import build_clause_nodes
from backend.app.core.config import get_settings
from backend.app.db.qdrant import get_qdrant_client
from backend.app.schemas.rag import CitationSource, RetrievedChunk
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.embeddings import get_embeddings_service
from backend.app.services.generation import GeminiClient
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.reranker import LLMReranker, RerankedRetriever
from backend.app.services.retrieval import QdrantRetriever

logger = logging.getLogger(__name__)


# ── Clause pipeline state ──────────────────────────────────────────────────────

class ClauseState(TypedDict, total=False):
    """State flowing through the three-node clause generator pipeline."""

    # ── Input (provided by caller) ─────────────────────────────────────────────
    request: str              # "Draft a UBO disclosure clause for..."
    document_type_hint: str   # optional caller hint, used by parse_request
    top_k: int                # how many context chunks to retrieve

    # ── Set by parse_request ───────────────────────────────────────────────────
    clause_type: str          # e.g. "ubo_disclosure"
    document_type: str        # e.g. "articles_of_association"
    key_requirements: list[str]

    # ── Set by retrieve_context ────────────────────────────────────────────────
    retrieved_chunks: list[RetrievedChunk]

    # ── Set by generate_clause ─────────────────────────────────────────────────
    clause_text: str
    citations: list[CitationSource]
    model: str


# ── Graph factory ──────────────────────────────────────────────────────────────

def build_clause_graph(retriever: Any, gemini: GeminiClient) -> Any:
    """Construct and compile the three-node clause generator sub-graph.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object.
    gemini:
        ``GeminiClient`` instance shared across all nodes.
    """
    nodes = build_clause_nodes(retriever=retriever, gemini=gemini)

    graph: StateGraph = StateGraph(ClauseState)
    for name, fn in nodes.items():
        graph.add_node(name, fn)

    graph.add_edge(START,              "parse_request")
    graph.add_edge("parse_request",    "retrieve_context")
    graph.add_edge("retrieve_context", "generate_clause")
    graph.add_edge("generate_clause",  END)

    compiled = graph.compile()
    logger.info("Clause generator sub-graph compiled.")
    return compiled


@lru_cache(maxsize=1)
def get_compiled_clause_graph() -> Any:
    """Build and cache the clause generator graph with its full retrieval stack.

    Call ``get_compiled_clause_graph.cache_clear()`` in tests.
    """
    settings  = get_settings()
    embeddings = get_embeddings_service(settings=settings)
    qdrant    = get_qdrant_client()

    dense     = QdrantRetriever(qdrant_client=qdrant, embeddings_service=embeddings)
    sparse    = BM25Retriever()
    hybrid    = HybridRetriever(dense=dense, sparse=sparse)
    gemini    = GeminiClient(settings=settings)
    reranker  = LLMReranker(client=gemini)
    retriever = RerankedRetriever(base=hybrid, reranker=reranker, candidate_pool=15)

    return build_clause_graph(retriever=retriever, gemini=gemini)
