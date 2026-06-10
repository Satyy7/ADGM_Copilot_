"""LangGraph compliance workflow graph (Phase 8+).

Graph topology
--------------

    START
      │
      ▼
  route_intent          ← LLM classifies question into one of four intents
      │
      ├─► retrieve ──► generate ──► END   (compliance_chat)
      ├─► handle_review          ──► END   (compliance_review  — Phase 9 stub)
      ├─► handle_clause_gen      ──► END   (clause_generation  — Phase 10 stub)
      └─► handle_analytics       ──► END   (analytics          — Phase 12 stub)

Evolution
---------
Phase 8:  current file — chat path fully functional, others stubbed.
Phase 9:  replace ``handle_review`` with a sub-graph of 6 specialist agents.
Phase 10: replace ``handle_clause_gen`` with the clause generator sub-graph.
Phase 12: replace ``handle_analytics`` with the Text2SQL sub-graph.
Phase 13: HyDE wraps the retrieval stack (service layer, graph unchanged).
Phase 14: CRAG gate — retrieve → crag_evaluate → (rewrite?) → generate.
Phase 15: add Self-RAG scoring node before ``generate``.

Because every capability is a separate branch off ``route_intent``, adding
or replacing a branch never affects the other paths.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from backend.app.agent.crag.nodes import build_crag_nodes, select_crag_path
from backend.app.agent.nodes import build_nodes, select_path
from backend.app.agent.self_rag.nodes import build_self_rag_nodes
from backend.app.agent.state import AgentState
from backend.app.core.config import get_settings
from backend.app.db.qdrant import get_qdrant_client
from backend.app.db.redis import get_redis_client
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.cached_retriever import CachedRetriever
from backend.app.services.embeddings import get_embeddings_service
from backend.app.services.generation import GeminiClient
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.hyde_retriever import HyDERetriever
from backend.app.services.reranker import LLMReranker, RerankedRetriever
from backend.app.services.retrieval import QdrantRetriever

logger = logging.getLogger(__name__)


def build_compliance_graph(retriever: object, gemini: GeminiClient) -> object:
    """Construct and compile the LangGraph compliance workflow.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object.  In Phase 13+ this is a
        ``HyDERetriever`` wrapping the full Hybrid+Reranked stack.
    gemini:
        ``GeminiClient`` shared by all nodes (intent router, generate,
        re-ranker, CRAG evaluator, query rewriter).

    Graph topology (Phase 15)
    -------------------------
    START → route_intent → {
      compliance_chat:
        retrieve
          → crag_evaluate
              ──(relevant/ambiguous)──► self_check_evidence
              └─(irrelevant)──► rewrite_and_retrieve → self_check_evidence
          → generate
          → self_grade_answer → END
      compliance_review     → handle_review     → END
      clause_generation     → handle_clause_gen → END
      analytics             → handle_analytics  → END
    }
    """
    nodes          = build_nodes(retriever=retriever, gemini=gemini)
    crag_nodes     = build_crag_nodes(retriever=retriever, gemini=gemini)
    self_rag_nodes = build_self_rag_nodes(gemini=gemini)

    graph: StateGraph = StateGraph(AgentState)

    for name, fn in nodes.items():
        graph.add_node(name, fn)
    for name, fn in crag_nodes.items():
        graph.add_node(name, fn)
    for name, fn in self_rag_nodes.items():
        graph.add_node(name, fn)

    # Entry point
    graph.add_edge(START, "route_intent")

    # Intent routing
    graph.add_conditional_edges(
        "route_intent",
        select_path,
        {
            "retrieve":          "retrieve",
            "handle_review":     "handle_review",
            "handle_clause_gen": "handle_clause_gen",
            "handle_analytics":  "handle_analytics",
        },
    )

    # Phase 14: CRAG gate — routes to self_check_evidence, not directly to generate
    graph.add_edge("retrieve", "crag_evaluate")
    graph.add_conditional_edges(
        "crag_evaluate",
        select_crag_path,
        {
            "generate":             "self_check_evidence",  # Phase 15 inserted here
            "rewrite_and_retrieve": "rewrite_and_retrieve",
        },
    )
    graph.add_edge("rewrite_and_retrieve", "self_check_evidence")  # Phase 15

    # Phase 15: Self-RAG — evidence check before generate, grounding check after
    graph.add_edge("self_check_evidence", "generate")
    graph.add_edge("generate",            "self_grade_answer")
    graph.add_edge("self_grade_answer",   END)

    # Non-chat paths terminate immediately
    graph.add_edge("handle_review",     END)
    graph.add_edge("handle_clause_gen", END)
    graph.add_edge("handle_analytics",  END)

    compiled = graph.compile()
    logger.info("Compliance workflow graph compiled (CRAG + Self-RAG active).")
    return compiled


@lru_cache(maxsize=1)
def get_compiled_graph() -> object:
    """Build and cache the full retrieval stack + compiled graph.

    Called once per process lifetime.  Call ``get_compiled_graph.cache_clear()``
    in tests to reset between test cases.

    Retrieval stack (Phase 16)
    --------------------------
    QdrantRetriever (dense)  ─┐
    BM25Retriever   (sparse) ─┤→ HybridRetriever (RRF)
                               └→ RerankedRetriever (LLM listwise)
                                    └→ HyDERetriever (hypothetical doc expansion)
                                         └→ CachedRetriever (Redis, 30-min TTL)
    """
    settings   = get_settings()
    redis      = get_redis_client()           # Phase 16: shared cache client
    embeddings = get_embeddings_service(      # Phase 16: embedding cache active
        settings=settings,
        redis_client=redis,
    )
    qdrant     = get_qdrant_client()

    dense    = QdrantRetriever(qdrant_client=qdrant, embeddings_service=embeddings)
    sparse   = BM25Retriever()
    hybrid   = HybridRetriever(dense=dense, sparse=sparse)

    gemini   = GeminiClient(settings=settings, redis_client=redis)  # Phase 16: generate_text cache
    reranker = LLMReranker(client=gemini)
    reranked = RerankedRetriever(base=hybrid, reranker=reranker, candidate_pool=20)

    # Phase 13: wrap the full reranked stack with HyDE
    hyde      = HyDERetriever(base=reranked, gemini=gemini, enabled=True)

    # Phase 16: cache the entire retrieval stack (HyDE → Rerank → Hybrid → Dense+Sparse)
    retriever = CachedRetriever(base=hyde, redis_client=redis)

    return build_compliance_graph(retriever=retriever, gemini=gemini)
