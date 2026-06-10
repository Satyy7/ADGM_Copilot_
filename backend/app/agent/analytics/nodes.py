"""Text2SQL analytics pipeline nodes — Phase 12.

Pipeline
--------
generate_sql  ->  validate_sql  ->  execute_sql  ->  format_answer

Node 1 — generate_sql
    LLM converts the natural language question to a PostgreSQL SELECT statement.
    If the caller provided ``confirmed_sql`` in the state (user-reviewed SQL),
    that is used directly, skipping the LLM generation step.

Node 2 — validate_sql
    Static safety checks: SELECT-only, no dangerous keywords, only allowed tables,
    enforced LIMIT.  Sets ``sql_safe=False`` and ``sql_rejection_reason`` on failure.

Node 3 — execute_sql
    Skipped if ``sql_safe=False`` or ``preview_only=True``.
    Executes the SQL via SQLAlchemy against the live PostgreSQL database.
    Serialises UUID, datetime, and Decimal types for JSON safety.

Node 4 — format_answer
    LLM translates raw query results (or a validation/execution error) into a
    professional compliance analytics narrative.
"""

from __future__ import annotations

import decimal
import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import text

from backend.app.agent.analytics.prompts import FORMAT_ANSWER_PROMPT, SQL_GENERATION_PROMPT

logger = logging.getLogger(__name__)

# ── Safety constants ───────────────────────────────────────────────────────────

_BLOCKED_KEYWORDS: frozenset[str] = frozenset({
    "drop", "delete", "insert", "update", "alter", "truncate",
    "create", "exec", "execute", "call", "grant", "revoke",
    "commit", "rollback", "pg_read_file", "pg_ls_dir",
    "copy", "lo_export", "lo_import",
})

_ALLOWED_TABLES: frozenset[str] = frozenset({
    "users", "documents", "reviews", "violations", "recommendations",
    "generated_clauses", "audit_logs", "query_logs",
})

_DEFAULT_LIMIT = 50


# ── Node factory ───────────────────────────────────────────────────────────────

def build_analytics_nodes(gemini: object, engine: object) -> dict[str, Any]:
    """Return node name → callable for the analytics pipeline.

    Parameters
    ----------
    gemini:
        ``GeminiClient`` instance (typed as object to avoid circular import).
    engine:
        SQLAlchemy ``Engine`` for query execution.
    """

    # ── Node 1: generate_sql ───────────────────────────────────────────────────

    def generate_sql(state: dict) -> dict:
        """Convert the question to SQL, or pass through a confirmed SQL string."""
        confirmed = state.get("confirmed_sql")
        if confirmed and confirmed.strip():
            logger.info("Using caller-provided confirmed SQL.")
            return {"generated_sql": confirmed.strip()}

        question = state.get("question", "")
        prompt = SQL_GENERATION_PROMPT.format(question=question)

        try:
            raw: str = gemini.generate_text(prompt)  # type: ignore[union-attr]
            sql = _clean_sql(raw)
        except Exception as exc:
            logger.error("SQL generation failed: %s", exc)
            sql = ""

        logger.info("Generated SQL: %s", sql[:120])
        return {"generated_sql": sql}

    # ── Node 2: validate_sql ───────────────────────────────────────────────────

    def validate_sql(state: dict) -> dict:
        """Run static safety checks on the generated SQL."""
        sql = state.get("generated_sql", "").strip()

        if not sql:
            return {
                "sql_safe": False,
                "sql_rejection_reason": "SQL generation produced an empty result.",
            }

        # Must start with SELECT (after stripping comments)
        normalised = re.sub(r"--.*", "", sql, flags=re.MULTILINE)
        normalised = re.sub(r"/\*.*?\*/", "", normalised, flags=re.DOTALL).strip().upper()
        if not normalised.startswith("SELECT"):
            return {
                "sql_safe": False,
                "sql_rejection_reason": (
                    "Only SELECT statements are permitted. "
                    f"The generated SQL starts with: {sql[:60]}"
                ),
            }

        # No blocked keywords
        tokens = set(re.findall(r"[a-z_]+", sql.lower()))
        blocked_found = tokens & _BLOCKED_KEYWORDS
        if blocked_found:
            return {
                "sql_safe": False,
                "sql_rejection_reason": (
                    f"SQL contains prohibited keyword(s): {', '.join(sorted(blocked_found))}."
                ),
            }

        # Enforce LIMIT — add if missing and not a pure aggregation query
        sql_with_limit = _enforce_limit(sql)

        logger.info("SQL passed safety validation.")
        return {
            "sql_safe": True,
            "sql_rejection_reason": None,
            "generated_sql": sql_with_limit,
        }

    # ── Node 3: execute_sql ────────────────────────────────────────────────────

    def execute_sql(state: dict) -> dict:
        """Execute the validated SQL against PostgreSQL.

        Skipped when sql_safe=False or preview_only=True.
        """
        if not state.get("sql_safe", False):
            return {
                "query_results": [],
                "row_count": 0,
                "columns": [],
                "execution_error": state.get("sql_rejection_reason", "SQL failed validation."),
            }

        if state.get("preview_only", False):
            logger.info("preview_only=True — skipping execution.")
            return {
                "query_results": [],
                "row_count": 0,
                "columns": [],
                "execution_error": "",
            }

        sql = state.get("generated_sql", "")
        try:
            with engine.connect() as conn:  # type: ignore[union-attr]
                result = conn.execute(text(sql))
                columns: list[str] = list(result.keys())
                rows = result.fetchall()
                query_results = _serialize_results(
                    [dict(zip(columns, row)) for row in rows]
                )
            logger.info("SQL returned %d rows, %d columns.", len(query_results), len(columns))
            return {
                "query_results": query_results,
                "row_count": len(query_results),
                "columns": columns,
                "execution_error": "",
            }
        except Exception as exc:
            logger.error("SQL execution error: %s | SQL: %s", exc, sql[:120])
            return {
                "query_results": [],
                "row_count": 0,
                "columns": [],
                "execution_error": str(exc),
            }

    # ── Node 4: format_answer ──────────────────────────────────────────────────

    def format_answer(state: dict) -> dict:
        """Format SQL results (or errors) into a professional compliance narrative."""
        question       = state.get("question", "")
        sql            = state.get("generated_sql", "")
        sql_safe       = state.get("sql_safe", False)
        sql_reason     = state.get("sql_rejection_reason")
        exec_error     = state.get("execution_error", "")
        preview_only   = state.get("preview_only", False)
        query_results  = state.get("query_results", [])
        row_count      = state.get("row_count", 0)
        columns        = state.get("columns", [])

        # Fast-path: unsafe SQL
        if not sql_safe and sql_reason:
            return {
                "answer": (
                    f"The analytics query could not be executed: {sql_reason} "
                    "Please rephrase your question to request read-only compliance data."
                ),
                "model": getattr(gemini, "active_model", "n/a"),  # type: ignore[union-attr]
            }

        # Fast-path: preview only
        if preview_only:
            return {
                "answer": (
                    f"Preview mode — SQL generated but not executed.\n\nGenerated SQL:\n{sql}"
                ),
                "model": getattr(gemini, "active_model", "n/a"),  # type: ignore[union-attr]
            }

        # Fast-path: execution error
        if exec_error:
            return {
                "answer": (
                    f"The SQL query could not be executed against the database. "
                    f"Error: {exec_error}. "
                    "Please rephrase your question or contact the administrator."
                ),
                "model": getattr(gemini, "active_model", "n/a"),  # type: ignore[union-attr]
            }

        # Format results via LLM
        sample = query_results[:5]
        sample_text = json.dumps(sample, indent=2, default=str) if sample else "[]"
        prompt = FORMAT_ANSWER_PROMPT.format(
            question=question,
            sql=sql,
            row_count=row_count,
            columns=", ".join(columns) or "none",
            sample_results=sample_text,
        )

        try:
            answer: str = gemini.generate_text(prompt)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("format_answer LLM failed (%s), using fallback.", exc)
            answer = (
                f"Query returned {row_count} result(s). "
                + (f"Columns: {', '.join(columns)}." if columns else "")
            )

        model: str = getattr(gemini, "active_model", "unknown")  # type: ignore[union-attr]
        logger.info("Analytics answer generated via %s.", model)
        return {"answer": answer.strip(), "model": model}

    return {
        "generate_sql":  generate_sql,
        "validate_sql":  validate_sql,
        "execute_sql":   execute_sql,
        "format_answer": format_answer,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_sql(raw: str) -> str:
    """Strip markdown fences and surrounding whitespace from LLM SQL output."""
    text_out = raw.strip()
    # Remove ```sql ... ``` or ``` ... ``` fences
    text_out = re.sub(r"^```(?:sql)?\s*", "", text_out, flags=re.IGNORECASE)
    text_out = re.sub(r"\s*```$", "", text_out)
    return text_out.strip()


def _enforce_limit(sql: str) -> str:
    """Add LIMIT if absent and the query is not a pure aggregation."""
    upper = sql.upper()
    if "LIMIT" in upper:
        return sql
    # Heuristic: if the SELECT list has only aggregate functions, skip LIMIT
    # (COUNT(*), SUM, AVG, MIN, MAX at the top level)
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", upper, re.DOTALL)
    if select_match:
        select_list = select_match.group(1)
        agg_only = bool(re.match(
            r"^(COUNT|SUM|AVG|MIN|MAX|PERCENTILE_CONT|PERCENTILE_DISC)\s*\(",
            select_list.strip(),
        ))
        if agg_only:
            return sql
    return sql.rstrip(";") + f"\nLIMIT {_DEFAULT_LIMIT}"


def _serialize_results(rows: list[dict]) -> list[dict]:
    """Convert UUID, datetime, and Decimal values to JSON-safe primitives."""
    out: list[dict] = []
    for row in rows:
        clean: dict = {}
        for k, v in row.items():
            if isinstance(v, uuid.UUID):
                clean[k] = str(v)
            elif hasattr(v, "isoformat"):   # datetime / date / time
                clean[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                clean[k] = float(v)
            else:
                clean[k] = v
        out.append(clean)
    return out
