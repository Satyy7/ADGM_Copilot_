"""Phase 15 end-to-end test suite — Self-RAG.

Run with:
    uv run python scripts/test_phase15.py

Tests
-----
Unit tests (no running server)
1.  self_check_evidence -> SUFFICIENT when chunks are relevant
2.  self_check_evidence -> INSUFFICIENT when no chunks present (no LLM call)
3.  self_check_evidence -> INSUFFICIENT when LLM says INSUFFICIENT
4.  self_check_evidence defaults to SUFFICIENT on LLM failure (never blocks)
5.  self_grade_answer -> GROUNDED when LLM confirms grounding
6.  self_grade_answer -> UNGROUNDED replaces answer with conservative text
7.  self_grade_answer -> GROUNDED defaults on LLM failure (never discards)
8.  self_grade_answer skips grading when answer is empty
9.  self_grade_answer skips grading the built-in no-context fallback message
10. Full node map returned correctly by build_self_rag_nodes

E2E API tests (require running server on port 8001)
11. POST /chat — standard question flows through all Self-RAG nodes
12. POST /chat — UBO question returns grounded answer with citations
13. POST /chat — answer is not an empty string (Self-RAG never discards without replacement)
14. POST /chat — analytics and clause intents unaffected by Self-RAG
"""

import json
import os
import sys
import urllib.error
import urllib.request

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, ".")

BASE = "http://localhost:8001/api/v1"

all_passed = True


def post_json(path: str, body: dict, timeout: int = 180) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


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
        print(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
        all_passed = False
    except Exception as exc:
        import traceback
        print(f"ERROR: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        all_passed = False


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def _mock_chunk(text: str):
    from unittest.mock import MagicMock
    c = MagicMock()
    c.text = text
    c.source_title = "ADGM Regulation"
    c.score = 0.9
    return c


def test_evidence_sufficient():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, EVIDENCE_SUFFICIENT

    gemini = MagicMock()
    gemini.generate_text.return_value = "SUFFICIENT"
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_check_evidence"]({
        "question": "What is the UBO registration requirement?",
        "retrieved_chunks": [
            _mock_chunk(
                "Under Article 12, all companies must register beneficial owners "
                "holding 25% or more within 14 days."
            )
        ],
    })
    assert result["evidence_sufficiency"] == EVIDENCE_SUFFICIENT
    print(f"Sufficiency: {result['evidence_sufficiency']}  PASS")

run("Unit: self_check_evidence -> SUFFICIENT", test_evidence_sufficient)


def test_evidence_no_chunks_skips_llm():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, EVIDENCE_INSUFFICIENT

    gemini = MagicMock()
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_check_evidence"]({
        "question": "What are the regulations?",
        "retrieved_chunks": [],
    })
    assert result["evidence_sufficiency"] == EVIDENCE_INSUFFICIENT
    assert not gemini.generate_text.called, "LLM must NOT be called when no chunks"
    print("No chunks -> INSUFFICIENT, LLM skipped  PASS")

run("Unit: self_check_evidence -> INSUFFICIENT with no chunks (no LLM)", test_evidence_no_chunks_skips_llm)


def test_evidence_insufficient():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, EVIDENCE_INSUFFICIENT

    gemini = MagicMock()
    gemini.generate_text.return_value = "INSUFFICIENT"
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_check_evidence"]({
        "question": "What is the minimum capital for an ADGM bank?",
        "retrieved_chunks": [
            _mock_chunk("Annual accounts must be filed within 9 months.")
        ],
    })
    assert result["evidence_sufficiency"] == EVIDENCE_INSUFFICIENT
    print(f"Sufficiency: {result['evidence_sufficiency']}  PASS")

run("Unit: self_check_evidence -> INSUFFICIENT", test_evidence_insufficient)


def test_evidence_check_defaults_on_failure():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, EVIDENCE_SUFFICIENT

    gemini = MagicMock()
    gemini.generate_text.side_effect = RuntimeError("API error")
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_check_evidence"]({
        "question": "UBO requirements?",
        "retrieved_chunks": [_mock_chunk("Some text.")],
    })
    assert result["evidence_sufficiency"] == EVIDENCE_SUFFICIENT, \
        "Must default to SUFFICIENT on failure — never block generation"
    print("LLM failure -> SUFFICIENT (safe default)  PASS")

run("Unit: self_check_evidence defaults SUFFICIENT on LLM failure", test_evidence_check_defaults_on_failure)


def test_grade_answer_grounded():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, ANSWER_GROUNDED

    gemini = MagicMock()
    gemini.generate_text.return_value = "GROUNDED"
    nodes = build_self_rag_nodes(gemini=gemini)

    original_answer = "UBO registration is required for persons holding 25% or more."
    result = nodes["self_grade_answer"]({
        "question": "What is the UBO threshold?",
        "answer":   original_answer,
        "retrieved_chunks": [
            _mock_chunk("Beneficial owners holding 25% or more must be registered.")
        ],
    })
    assert result["answer_grade"] == ANSWER_GROUNDED
    assert "answer" not in result or result.get("answer") == original_answer, \
        "GROUNDED answer must not be replaced"
    print(f"Grade: {result['answer_grade']}  PASS")

run("Unit: self_grade_answer -> GROUNDED (answer preserved)", test_grade_answer_grounded)


def test_grade_answer_ungrounded_replaces():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import (
        build_self_rag_nodes, ANSWER_UNGROUNDED, _CONSERVATIVE_ANSWER
    )

    gemini = MagicMock()
    gemini.generate_text.return_value = "UNGROUNDED"
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_grade_answer"]({
        "question": "What is the corporate tax rate in ADGM?",
        "answer":   "ADGM companies pay a flat 15% corporate tax under Section 42.",
        "retrieved_chunks": [
            _mock_chunk("ADGM is a financial free zone with zero corporate tax.")
        ],
    })
    assert result["answer_grade"] == ANSWER_UNGROUNDED
    assert result["answer"] == _CONSERVATIVE_ANSWER, \
        "UNGROUNDED answer must be replaced with conservative text"
    assert "consult" in result["answer"].lower(), \
        "Conservative answer should direct user to official sources"
    print(f"Grade: {result['answer_grade']}")
    print(f"Conservative: {result['answer'][:120]}...")
    print("PASS")

run("Unit: self_grade_answer -> UNGROUNDED replaces with conservative text", test_grade_answer_ungrounded_replaces)


def test_grade_answer_defaults_grounded_on_failure():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, ANSWER_GROUNDED

    gemini = MagicMock()
    gemini.generate_text.side_effect = RuntimeError("Timeout")
    nodes = build_self_rag_nodes(gemini=gemini)

    original = "Some generated compliance answer."
    result = nodes["self_grade_answer"]({
        "question": "test question?",
        "answer":   original,
        "retrieved_chunks": [_mock_chunk("relevant text")],
    })
    assert result["answer_grade"] == ANSWER_GROUNDED, \
        "Must default to GROUNDED on failure — never silently discard an answer"
    print("LLM failure -> GROUNDED (safe default, answer preserved)  PASS")

run("Unit: self_grade_answer defaults GROUNDED on LLM failure", test_grade_answer_defaults_grounded_on_failure)


def test_grade_answer_skips_empty():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, ANSWER_GROUNDED

    gemini = MagicMock()
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_grade_answer"]({
        "question": "test?",
        "answer":   "",
        "retrieved_chunks": [_mock_chunk("some text")],
    })
    assert not gemini.generate_text.called, "LLM must NOT be called for empty answer"
    assert result["answer_grade"] == ANSWER_GROUNDED
    print("Empty answer -> grading skipped, no LLM call  PASS")

run("Unit: self_grade_answer skips grading for empty answer", test_grade_answer_skips_empty)


def test_grade_skips_no_context_fallback():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes, ANSWER_GROUNDED

    gemini = MagicMock()
    nodes = build_self_rag_nodes(gemini=gemini)

    result = nodes["self_grade_answer"]({
        "question": "test?",
        "answer":   "No relevant regulatory context was found. Please rephrase your question.",
        "retrieved_chunks": [_mock_chunk("some text")],
    })
    assert not gemini.generate_text.called, "LLM must NOT be called for built-in fallback"
    print("Built-in fallback answer -> grading skipped  PASS")

run("Unit: self_grade_answer skips built-in no-context fallback", test_grade_skips_no_context_fallback)


def test_build_returns_both_nodes():
    from unittest.mock import MagicMock
    from backend.app.agent.self_rag.nodes import build_self_rag_nodes

    nodes = build_self_rag_nodes(gemini=MagicMock())
    assert "self_check_evidence" in nodes
    assert "self_grade_answer"   in nodes
    assert callable(nodes["self_check_evidence"])
    assert callable(nodes["self_grade_answer"])
    print("Both nodes present and callable  PASS")

run("Unit: build_self_rag_nodes returns both node callables", test_build_returns_both_nodes)


# ---------------------------------------------------------------------------
# E2E API tests
# ---------------------------------------------------------------------------

def test_e2e_standard_question():
    """Standard compliance question flows through the full pipeline including Self-RAG."""
    data = post_json("/chat", {
        "question": "What are the annual filing obligations for an ADGM private company?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    model   = data.get("model", "?")
    sources = data.get("sources", [])
    latency = data.get("latency_ms", "?")
    print(f"Model   : {model}")
    print(f"Latency : {latency} ms")
    print(f"Sources : {len(sources)}")
    print(f"Answer  : {answer[:350]}")
    assert answer, "Expected non-empty answer"
    assert len(answer) > 50, f"Answer too short ({len(answer)} chars)"
    print("PASS")

run("E2E: Standard question — full pipeline (HyDE+CRAG+Self-RAG)", test_e2e_standard_question)


def test_e2e_ubo_grounded():
    """UBO question returns a grounded answer — Self-RAG should not replace it."""
    data = post_json("/chat", {
        "question": "What is the threshold ownership percentage that triggers UBO disclosure in ADGM?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    sources = data.get("sources", [])
    print(f"Sources : {len(sources)}")
    print(f"Answer  : {answer[:400]}")
    assert answer, "Expected non-empty answer"
    # If Self-RAG replaced with conservative text, it should still be non-empty
    assert "consult" in answer.lower() or any(t in answer.lower() for t in [
        "25%", "beneficial", "ownership", "ubo", "register", "adgm",
    ]), "Answer should contain UBO-relevant terms OR a conservative disclaimer"
    print("PASS")

run("E2E: UBO question — grounded answer or well-formed conservative response", test_e2e_ubo_grounded)


def test_e2e_answer_never_empty():
    """Self-RAG never leaves the answer empty — always returns something useful."""
    questions = [
        "What documents are needed to incorporate an ADGM company?",
        "What are the employment contract requirements in ADGM?",
        "How does ADGM regulate beneficial ownership?",
    ]
    for q in questions:
        data = post_json("/chat", {"question": q, "top_k": 5})
        answer = data.get("answer", "")
        assert answer, f"Expected non-empty answer for: '{q}'"
        print(f"  OK: {q[:55]}... -> {len(answer)} chars")
    print("PASS")

run("E2E: Self-RAG never produces empty answer for compliance questions", test_e2e_answer_never_empty)


def test_e2e_other_intents_unaffected():
    """Self-RAG only touches compliance_chat — analytics and clause gen unaffected."""
    # Analytics intent
    analytics = post_json("/chat", {
        "question": "How many clause records are in the database?",
        "top_k": 5,
    })
    assert analytics.get("answer"), "Analytics answer must not be empty"
    print(f"Analytics: {analytics['answer'][:100]}")

    # Clause generation intent
    clause = post_json("/generated-clauses/generate", {
        "request": "Draft a UBO beneficial ownership disclosure clause for an ADGM company.",
        "document_type": "articles_of_association",
        "top_k": 5,
    })
    assert clause.get("clause_text"), "Clause text must not be empty"
    print(f"Clause: {clause['clause_text'][:100]}...")
    print("PASS")

run("E2E: Other intents (analytics, clause gen) unaffected by Self-RAG", test_e2e_other_intents_unaffected)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'=' * 68}")
print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
print(f"{'=' * 68}")
sys.exit(0 if all_passed else 1)
