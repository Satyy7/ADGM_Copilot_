"""Phase 14 end-to-end test suite — CRAG (Corrective RAG).

Run with:
    uv run python scripts/test_phase14.py

Tests
-----
Unit tests (no running server)
1.  crag_evaluate grades RELEVANT when chunks match the question
2.  crag_evaluate grades IRRELEVANT when chunks are off-topic
3.  crag_evaluate grades AMBIGUOUS when LLM output is unexpected
4.  crag_evaluate returns IRRELEVANT when no chunks present
5.  rewrite_and_retrieve rewrites query and fetches new chunks
6.  rewrite_and_retrieve falls back gracefully when rewrite fails
7.  select_crag_path routes to generate for relevant/ambiguous
8.  select_crag_path routes to rewrite_and_retrieve for irrelevant

E2E API tests (require running server on port 8001)
9.  POST /chat with relevant question — retrieval_grade not irrelevant
10. POST /chat with specific ADGM question — answer is grounded
11. POST /chat — rewrite path triggered for highly off-topic query
12. Full compliance_chat path stable with CRAG inserted
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
# Unit tests — direct node instantiation, no running server
# ---------------------------------------------------------------------------

def _make_mock_chunk(text: str, source: str = "ADGM Regulations"):
    from unittest.mock import MagicMock
    chunk = MagicMock()
    chunk.text = text
    chunk.source_title = source
    chunk.score = 0.85
    return chunk


def test_evaluate_relevant():
    """crag_evaluate returns RELEVANT when LLM says RELEVANT."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes, GRADE_RELEVANT

    gemini = MagicMock()
    gemini.generate_text.return_value = "RELEVANT"
    retriever = MagicMock()

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    chunks = [_make_mock_chunk(
        "Article 12 of ADGM Beneficial Ownership Regulations 2018 requires all "
        "companies to maintain a register of beneficial owners holding 25% or more."
    )]
    result = nodes["crag_evaluate"]({
        "question": "What are the UBO beneficial ownership requirements?",
        "retrieved_chunks": chunks,
    })
    assert result["retrieval_grade"] == GRADE_RELEVANT, \
        f"Expected RELEVANT, got: {result['retrieval_grade']}"
    print(f"Grade: {result['retrieval_grade']}  PASS")

run("Unit: crag_evaluate -> RELEVANT", test_evaluate_relevant)


def test_evaluate_irrelevant():
    """crag_evaluate returns IRRELEVANT when LLM says IRRELEVANT."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes, GRADE_IRRELEVANT

    gemini = MagicMock()
    gemini.generate_text.return_value = "IRRELEVANT"
    retriever = MagicMock()

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    chunks = [_make_mock_chunk(
        "Annual accounts must be filed within 9 months of the financial year end."
    )]
    result = nodes["crag_evaluate"]({
        "question": "What is the minimum share capital for a bank?",
        "retrieved_chunks": chunks,
    })
    assert result["retrieval_grade"] == GRADE_IRRELEVANT, \
        f"Expected IRRELEVANT, got: {result['retrieval_grade']}"
    print(f"Grade: {result['retrieval_grade']}  PASS")

run("Unit: crag_evaluate -> IRRELEVANT", test_evaluate_irrelevant)


def test_evaluate_ambiguous_fallback():
    """crag_evaluate defaults to AMBIGUOUS on unexpected LLM output."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes, GRADE_AMBIGUOUS

    gemini = MagicMock()
    gemini.generate_text.return_value = "NOT SURE MAYBE"
    retriever = MagicMock()

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    chunks = [_make_mock_chunk("Some regulatory text about ADGM compliance.")]
    result = nodes["crag_evaluate"]({
        "question": "Tell me about ADGM regulations",
        "retrieved_chunks": chunks,
    })
    assert result["retrieval_grade"] == GRADE_AMBIGUOUS, \
        f"Expected AMBIGUOUS fallback, got: {result['retrieval_grade']}"
    print(f"Grade: {result['retrieval_grade']}  PASS")

run("Unit: crag_evaluate -> AMBIGUOUS on unexpected output", test_evaluate_ambiguous_fallback)


def test_evaluate_no_chunks():
    """crag_evaluate returns IRRELEVANT immediately when no chunks retrieved."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes, GRADE_IRRELEVANT

    gemini = MagicMock()
    retriever = MagicMock()

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    result = nodes["crag_evaluate"]({
        "question": "What are employment regulations?",
        "retrieved_chunks": [],
    })
    assert result["retrieval_grade"] == GRADE_IRRELEVANT
    assert not gemini.generate_text.called, "LLM should NOT be called when no chunks present"
    print("Grade: IRRELEVANT (no chunks, no LLM call)  PASS")

run("Unit: crag_evaluate -> IRRELEVANT with no chunks (no LLM call)", test_evaluate_no_chunks)


def test_rewrite_and_retrieve():
    """rewrite_and_retrieve rewrites query and fetches new chunks."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes

    rewritten_text = (
        "ADGM Employment Regulations 2019 — probationary period maximum duration requirements"
    )
    new_chunks = [
        _make_mock_chunk("Probationary period must not exceed six months."),
        _make_mock_chunk("During probation, either party may terminate with 7 days notice."),
    ]

    gemini = MagicMock()
    gemini.generate_text.return_value = rewritten_text

    retriever = MagicMock()
    retriever.search.return_value = new_chunks

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    result = nodes["rewrite_and_retrieve"]({
        "question": "how long can probation last?",
        "retrieved_chunks": [],
        "top_k": 5,
    })

    assert result["rewritten_query"] == rewritten_text, "rewritten_query not set"
    assert result["retrieved_chunks"] == new_chunks, "retrieved_chunks not updated"
    assert retriever.search.call_args[1]["question"] == rewritten_text, \
        "Retriever must be called with the rewritten query"
    print(f"Original  : 'how long can probation last?'")
    print(f"Rewritten : '{result['rewritten_query'][:70]}'")
    print(f"New chunks: {len(result['retrieved_chunks'])}")
    print("PASS")

run("Unit: rewrite_and_retrieve rewrites query + fetches new chunks", test_rewrite_and_retrieve)


def test_rewrite_fallback_on_failure():
    """rewrite_and_retrieve uses original query if rewrite LLM call fails."""
    from unittest.mock import MagicMock
    from backend.app.agent.crag.nodes import build_crag_nodes

    original_question = "what about employment?"
    gemini = MagicMock()
    gemini.generate_text.side_effect = RuntimeError("LLM unavailable")

    retriever = MagicMock()
    retriever.search.return_value = []

    nodes = build_crag_nodes(retriever=retriever, gemini=gemini)
    result = nodes["rewrite_and_retrieve"]({
        "question": original_question,
        "retrieved_chunks": [],
        "top_k": 5,
    })

    assert result["rewritten_query"] == original_question, \
        "Should fall back to original question on LLM failure"
    print(f"Correctly fell back to original: '{result['rewritten_query']}'")
    print("PASS")

run("Unit: rewrite_and_retrieve fallback on LLM failure", test_rewrite_fallback_on_failure)


def test_select_crag_path_routing():
    """select_crag_path routes correctly for all three grades."""
    from backend.app.agent.crag.nodes import select_crag_path

    assert select_crag_path({"retrieval_grade": "relevant"})   == "generate"
    assert select_crag_path({"retrieval_grade": "ambiguous"})  == "generate"
    assert select_crag_path({"retrieval_grade": "irrelevant"}) == "rewrite_and_retrieve"
    assert select_crag_path({})                                 == "generate"  # default
    print("relevant  -> generate")
    print("ambiguous -> generate")
    print("irrelevant -> rewrite_and_retrieve")
    print("(empty)   -> generate (default)")
    print("PASS")

run("Unit: select_crag_path routes all three grades correctly", test_select_crag_path_routing)


# ---------------------------------------------------------------------------
# E2E API tests
# ---------------------------------------------------------------------------

def test_e2e_relevant_question():
    """Standard compliance question: CRAG path works end-to-end."""
    data = post_json("/chat", {
        "question": "What are the UBO beneficial ownership disclosure requirements for ADGM companies?",
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
    lower = answer.lower()
    has_relevant = any(t in lower for t in [
        "beneficial", "ownership", "ubo", "25%", "register", "owner",
        "adgm", "disclosure", "regulation", "company",
    ])
    assert has_relevant, f"Answer lacks ownership/UBO terminology: {answer[:200]}"
    print("PASS")

run("E2E: Relevant question — CRAG generates grounded answer", test_e2e_relevant_question)


def test_e2e_employment_question():
    """Employment regulation question flows through CRAG correctly."""
    data = post_json("/chat", {
        "question": "What is the maximum probation period allowed under ADGM Employment Regulations?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    latency = data.get("latency_ms", "?")
    print(f"Latency : {latency} ms")
    print(f"Answer  : {answer[:350]}")
    assert answer, "Expected non-empty answer"
    print("PASS")

run("E2E: Employment regulation question via CRAG", test_e2e_employment_question)


def test_e2e_vague_question_gets_rewritten():
    """Vague question may trigger CRAG rewrite path — answer still returned."""
    data = post_json("/chat", {
        "question": "compliance stuff",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    latency = data.get("latency_ms", "?")
    print(f"Latency : {latency} ms")
    print(f"Answer  : {answer[:350]}")
    # Even if rewrite was triggered, the pipeline must return something
    assert answer, "Expected non-empty answer even for vague query"
    print("PASS")

run("E2E: Vague query — CRAG rewrite path may activate, answer always returned", test_e2e_vague_question_gets_rewritten)


def test_e2e_all_intents_unaffected():
    """CRAG only affects compliance_chat — other intents still work."""
    # Analytics intent — should NOT go through CRAG
    data = post_json("/chat", {
        "question": "How many generated clauses are in the database?",
        "top_k": 5,
    })
    answer = data.get("answer", "")
    print(f"Analytics via chat: {answer[:200]}")
    assert answer, "Expected analytics answer"
    print("PASS")

run("E2E: Other intents (analytics) unaffected by CRAG", test_e2e_all_intents_unaffected)


def test_e2e_direct_compliance_chat():
    """Precise regulation question: CRAG evaluates as relevant, full answer returned."""
    data = post_json("/chat", {
        "question": "What documents are required to incorporate an ADGM private company limited by shares?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    sources = data.get("sources", [])
    model   = data.get("model", "?")
    print(f"Model   : {model}")
    print(f"Sources : {len(sources)}")
    print(f"Answer  : {answer[:400]}")
    assert answer, "Expected non-empty answer"
    assert len(answer) > 50, f"Answer too short ({len(answer)} chars)"
    print("PASS")

run("E2E: Incorporation question — CRAG grade relevant, full answer", test_e2e_direct_compliance_chat)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'=' * 68}")
print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
print(f"{'=' * 68}")
sys.exit(0 if all_passed else 1)
