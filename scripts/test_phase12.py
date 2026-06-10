"""Phase 12 end-to-end test suite — Text2SQL Analytics.

Run with:
    uv run python scripts/test_phase12.py

Requires backend server running on port 8001.

Tests
-----
1. Aggregate query     — COUNT of all reviews
2. Listing query       — recent generated clauses
3. Violation analysis  — violations by severity (GROUP BY)
4. Compliance scores   — AVG compliance_score
5. Preview mode        — returns SQL without executing
6. Human approval flow — preview then confirm SQL
7. SQL injection block  — DROP TABLE blocked
8. Via chat router      — analytics intent classification
"""

import json
import os
import sys
import urllib.error
import urllib.request

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BASE = "http://localhost:8001/api/v1"


def post_json(path: str, body: dict, timeout: int = 120) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


all_passed = True


def run(label: str, fn):
    global all_passed
    print(f"\n{'=' * 68}")
    print(f"TEST: {label}")
    print(f"{'=' * 68}")
    try:
        fn()
    except AssertionError as exc:
        print(f"FAIL -- {exc}")
        all_passed = False
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:300]
        print(f"HTTP {exc.code}: {body}")
        all_passed = False
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        all_passed = False


# ---------------------------------------------------------------------------
# Test 1: Aggregate count of reviews
# ---------------------------------------------------------------------------
def test_count_reviews():
    data = post_json("/analytics/query", {
        "question": "How many compliance reviews are in the database?",
    })
    print(f"SQL      : {data.get('generated_sql', '')[:120]}")
    print(f"sql_safe : {data.get('sql_safe')}")
    print(f"Rows     : {data.get('row_count')}")
    print(f"Answer   : {data.get('answer', '')[:200]}")
    print(f"Model    : {data.get('model')}")
    print(f"Latency  : {data.get('latency_ms')} ms")
    assert data.get("sql_safe") is True, "Expected sql_safe=True"
    assert data.get("generated_sql", "").upper().startswith("SELECT"), "SQL must start with SELECT"
    assert data.get("answer"), "Expected non-empty answer"
    print("PASS")

run("Aggregate count of reviews", test_count_reviews)

# ---------------------------------------------------------------------------
# Test 2: List generated clauses
# ---------------------------------------------------------------------------
def test_list_clauses():
    data = post_json("/analytics/query", {
        "question": "List the 5 most recent generated clauses with their clause type.",
    })
    print(f"SQL      : {data.get('generated_sql', '')[:120]}")
    print(f"sql_safe : {data.get('sql_safe')}")
    print(f"Rows     : {data.get('row_count')}")
    print(f"Answer   : {data.get('answer', '')[:200]}")
    assert data.get("sql_safe") is True
    assert data.get("answer")
    sql = data.get("generated_sql", "").lower()
    assert "generated_clauses" in sql or "clause" in sql, "Expected generated_clauses table reference"
    print("PASS")

run("List recent generated clauses", test_list_clauses)

# ---------------------------------------------------------------------------
# Test 3: Violations by severity (GROUP BY)
# ---------------------------------------------------------------------------
def test_violations_by_severity():
    data = post_json("/analytics/query", {
        "question": "Show me the count of violations grouped by severity level.",
    })
    print(f"SQL      : {data.get('generated_sql', '')[:120]}")
    print(f"sql_safe : {data.get('sql_safe')}")
    print(f"Rows     : {data.get('row_count')}")
    print(f"Columns  : {data.get('columns')}")
    print(f"Results  : {data.get('query_results', [])[:3]}")
    print(f"Answer   : {data.get('answer', '')[:200]}")
    assert data.get("sql_safe") is True
    sql = data.get("generated_sql", "").lower()
    assert "violations" in sql, "Expected violations table"
    assert "group by" in sql or "count" in sql.lower(), "Expected GROUP BY or COUNT"
    assert data.get("answer")
    print("PASS")

run("Violations by severity (GROUP BY)", test_violations_by_severity)

# ---------------------------------------------------------------------------
# Test 4: Average compliance score
# ---------------------------------------------------------------------------
def test_avg_compliance_score():
    data = post_json("/analytics/query", {
        "question": "What is the average compliance score across all reviews?",
    })
    print(f"SQL      : {data.get('generated_sql', '')[:120]}")
    print(f"sql_safe : {data.get('sql_safe')}")
    print(f"Results  : {data.get('query_results', [])[:2]}")
    print(f"Answer   : {data.get('answer', '')[:200]}")
    assert data.get("sql_safe") is True
    sql = data.get("generated_sql", "").lower()
    assert "avg" in sql or "average" in sql, "Expected AVG aggregate"
    assert "reviews" in sql, "Expected reviews table"
    print("PASS")

run("Average compliance score", test_avg_compliance_score)

# ---------------------------------------------------------------------------
# Test 5: Preview mode (SQL returned, not executed)
# ---------------------------------------------------------------------------
def test_preview_mode():
    data = post_json("/analytics/query", {
        "question": "How many query logs are in the database?",
        "preview_only": True,
    })
    print(f"SQL        : {data.get('generated_sql', '')[:120]}")
    print(f"sql_safe   : {data.get('sql_safe')}")
    print(f"preview    : {data.get('preview_only')}")
    print(f"row_count  : {data.get('row_count')}")
    print(f"Answer     : {data.get('answer', '')[:200]}")
    assert data.get("preview_only") is True, "preview_only must be True in response"
    assert data.get("row_count", -1) == 0, "No rows should be returned in preview mode"
    assert data.get("generated_sql"), "SQL must be generated even in preview mode"
    assert "preview" in data.get("answer", "").lower() or "sql" in data.get("answer", "").lower(), \
        "Answer should mention preview mode"
    print("PASS")

run("Preview mode (SQL generated, not executed)", test_preview_mode)

# ---------------------------------------------------------------------------
# Test 6: Human approval flow — preview then confirm
# ---------------------------------------------------------------------------
def test_human_approval_flow():
    # Step 1: preview
    preview = post_json("/analytics/query", {
        "question": "How many users are registered in the system?",
        "preview_only": True,
    })
    reviewed_sql = preview.get("generated_sql", "")
    print(f"Step 1 (preview) SQL: {reviewed_sql[:120]}")
    assert reviewed_sql, "SQL must be generated in preview step"
    assert preview.get("row_count", -1) == 0, "No execution in preview"

    # Step 2: confirm with reviewed SQL
    confirmed = post_json("/analytics/query", {
        "question": "How many users are registered in the system?",
        "confirmed_sql": reviewed_sql,
    })
    print(f"Step 2 (execute) rows   : {confirmed.get('row_count')}")
    print(f"Step 2 (execute) columns: {confirmed.get('columns')}")
    print(f"Step 2 (execute) answer : {confirmed.get('answer', '')[:200]}")
    assert confirmed.get("sql_safe") is True
    assert not confirmed.get("preview_only"), "Should not be preview in step 2"
    assert confirmed.get("answer")
    print("PASS")

run("Human approval flow (preview -> confirm)", test_human_approval_flow)

# ---------------------------------------------------------------------------
# Test 7: SQL injection / destructive SQL blocked
# ---------------------------------------------------------------------------
def test_sql_injection_blocked():
    # confirmed_sql overrides LLM generation — validator must still catch DROP TABLE
    data = post_json("/analytics/query", {
        "question": "Show me all registered users",
        "confirmed_sql": "DROP TABLE users; SELECT 1",
    })
    print(f"sql_safe         : {data.get('sql_safe')}")
    print(f"rejection_reason : {data.get('sql_rejection_reason', '')[:120]}")
    print(f"answer           : {data.get('answer', '')[:200]}")
    assert data.get("sql_safe") is False, "Expected sql_safe=False for DROP TABLE"
    assert data.get("sql_rejection_reason"), "Expected a rejection reason"
    assert data.get("row_count", -1) == 0, "No rows must be returned for rejected SQL"
    print("PASS")

run("SQL injection blocked (DROP TABLE)", test_sql_injection_blocked)

# ---------------------------------------------------------------------------
# Test 8: Via chat intent router — analytics intent
# ---------------------------------------------------------------------------
def test_via_chat_router():
    data = post_json("/chat", {
        "question": "How many violations with high severity have been recorded in the database?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    model   = data.get("model", "?")
    latency = data.get("latency_ms", "?")
    print(f"Model   : {model}")
    print(f"Latency : {latency} ms")
    print(f"Answer  : {answer[:300]}")
    assert answer, "Expected a non-empty answer from chat router"
    print("PASS")

run("Via chat intent router (analytics path)", test_via_chat_router)

# ---------------------------------------------------------------------------
# Test 9: Query logs saved
# ---------------------------------------------------------------------------
def test_query_logs_saved():
    import urllib.request
    req = urllib.request.Request(f"{BASE}/query-logs", method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        logs = json.loads(r.read())
    analytics_logs = [l for l in logs if l.get("query_type") == "analytics"]
    print(f"Total query logs : {len(logs)}")
    print(f"Analytics logs   : {len(analytics_logs)}")
    assert len(analytics_logs) > 0, "Expected at least one analytics query log persisted"
    print("PASS")

run("Analytics queries persisted to query_logs", test_query_logs_saved)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'=' * 68}")
print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
print(f"{'=' * 68}")
sys.exit(0 if all_passed else 1)
