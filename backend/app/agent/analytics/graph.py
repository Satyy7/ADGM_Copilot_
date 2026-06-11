"""Text2SQL analytics LangGraph sub-graph — Phase 12.

Graph topology
--------------
    START
      |
      v
  generate_sql     (LLM: natural language -> PostgreSQL SELECT)
      |
      v
  validate_sql     (static safety: SELECT-only, blocked keywords, table whitelist)
      |
      v
  execute_sql      (SQLAlchemy: run against live Postgres; skipped on preview_only)
      |
      v
  format_answer    (LLM: results -> professional compliance narrative)
      |
      v
    END

State
-----
``AnalyticsState`` is standalone — the pipeline can be invoked from the dedicated
API endpoint OR from the main graph's ``handle_analytics`` node.

Usage
-----
    from backend.app.agent.analytics.graph import get_compiled_analytics_graph

    graph = get_compiled_analytics_graph()
    result = graph.invoke({
        "question": "How many high-severity violations were detected last month?",
        "preview_only": False,
    })
    # result["answer"]       — formatted narrative
    # result["generated_sql"]— executed SQL
    # result["query_results"]— raw rows as list[dict]
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from backend.app.agent.analytics.nodes import build_analytics_nodes
from backend.app.core.config import get_settings
from backend.app.db.postgres import get_postgres_engine
from backend.app.services.generation import GeminiClient

logger = logging.getLogger(__name__)


# ── Analytics pipeline state ───────────────────────────────────────────────────

class AnalyticsState(TypedDict, total=False):
    """State flowing through the four-node analytics pipeline."""

    # ── Input (provided by caller) ─────────────────────────────────────────────
    question: str           # natural language analytics question
    preview_only: bool      # True = generate SQL but do not execute
    confirmed_sql: str      # caller-reviewed SQL; skips LLM generation if set

    # ── Set by generate_sql ────────────────────────────────────────────────────
    generated_sql: str

    # ── Set by validate_sql ────────────────────────────────────────────────────
    sql_safe: bool
    sql_rejection_reason: str | None

    # ── Set by execute_sql ─────────────────────────────────────────────────────
    query_results: list[dict]
    row_count: int
    columns: list[str]
    execution_error: str | None

    # ── Set by format_answer ───────────────────────────────────────────────────
    answer: str
    model: str


# ── Graph factory ──────────────────────────────────────────────────────────────

def build_analytics_graph(gemini: GeminiClient, engine: Any) -> Any:
    """Construct and compile the four-node analytics sub-graph."""
    nodes = build_analytics_nodes(gemini=gemini, engine=engine)

    graph: StateGraph = StateGraph(AnalyticsState)
    for name, fn in nodes.items():
        graph.add_node(name, fn)

    graph.add_edge(START,            "generate_sql")
    graph.add_edge("generate_sql",   "validate_sql")
    graph.add_edge("validate_sql",   "execute_sql")
    graph.add_edge("execute_sql",    "format_answer")
    graph.add_edge("format_answer",  END)

    compiled = graph.compile()
    logger.info("Analytics sub-graph compiled.")
    return compiled


@lru_cache(maxsize=1)
def get_compiled_analytics_graph() -> Any:
    """Build and cache the analytics graph with its service dependencies.

    Call ``get_compiled_analytics_graph.cache_clear()`` in tests.
    """
    settings = get_settings()
    gemini   = GeminiClient(settings=settings)
    engine   = get_postgres_engine()
    return build_analytics_graph(gemini=gemini, engine=engine)
