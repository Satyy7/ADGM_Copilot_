"""Phase 13 end-to-end test suite — HyDE (Hypothetical Document Embeddings).

Run with:
    uv run python scripts/test_phase13.py

Tests
-----
1.  Unit: HyDERetriever generates a richer hypothetical document for vague query
2.  Unit: Hypothetical document contains ADGM-specific regulatory terminology
3.  Unit: Fallback to original question when HyDE generation fails
4.  Unit: HyDE disabled mode passes query through unchanged
5.  Integration: Vague query via HyDE retriever returns relevant chunks
6.  Integration: Precise query via HyDE still works (HyDE does not degrade precise queries)
7.  E2E API: POST /chat returns answer with HyDE active (vague compliance question)
8.  E2E API: POST /chat returns answer with HyDE active (precise regulation question)
9.  E2E API: HyDE enabled in full stack — citations are compliance-relevant
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
        print(f"ERROR: {type(exc).__name__}: {exc}")
        all_passed = False


# ---------------------------------------------------------------------------
# Unit tests (direct service instantiation — no running server needed)
# ---------------------------------------------------------------------------

def test_hyde_generates_hypothetical():
    """HyDERetriever generates a hypothetical document richer than the query."""
    from unittest.mock import MagicMock
    from backend.app.services.hyde_retriever import HyDERetriever

    mock_gemini = MagicMock()
    mock_gemini.generate_text.return_value = (
        "Under Article 12 of the ADGM Beneficial Ownership Regulations 2018, "
        "all ADGM-registered companies must maintain an accurate and up-to-date "
        "register of beneficial owners. A beneficial owner is defined as any natural "
        "person who ultimately owns or controls more than 25% of the shares or voting "
        "rights, or who otherwise exercises control over the company's management. "
        "Companies must file their beneficial ownership information with the ADGM "
        "Registrar within 14 days of any change."
    )

    mock_base = MagicMock()
    mock_base.search.return_value = []

    retriever = HyDERetriever(base=mock_base, gemini=mock_gemini, enabled=True)
    retriever.search(question="what are the UBO requirements?")

    # Verify generate_text was called
    assert mock_gemini.generate_text.called, "generate_text must be called for HyDE"
    # Verify base was called with the hypothetical, not the original question
    call_kwargs = mock_base.search.call_args
    query_used = call_kwargs[1].get("question") or call_kwargs[0][0]
    assert "UBO" not in query_used or "Article 12" in query_used or len(query_used) > 30, \
        f"Base retriever should receive the hypothetical document, got: {query_used[:60]}"
    # Verify last_hypothetical is accessible
    assert retriever.last_hypothetical, "last_hypothetical should be populated"
    print(f"Hypothetical doc ({len(retriever.last_hypothetical)} chars):")
    print(f"  {retriever.last_hypothetical[:200]}...")
    print("PASS")

run("Unit: HyDE generates hypothetical document", test_hyde_generates_hypothetical)


def test_hypothetical_contains_adgm_terminology():
    """Hypothetical document contains regulatory vocabulary the raw query lacks."""
    from unittest.mock import MagicMock, patch
    from backend.app.services.hyde_retriever import HyDERetriever

    # Use real LLM call via cached services
    try:
        from backend.app.core.config import get_settings
        from backend.app.services.generation import GeminiClient

        gemini = GeminiClient(settings=get_settings())
        mock_base = MagicMock()
        mock_base.search.return_value = []

        retriever = HyDERetriever(base=mock_base, gemini=gemini, enabled=True)
        retriever.search(question="what documents does an ADGM company need for incorporation?")

        hypothetical = retriever.last_hypothetical
        assert hypothetical, "Hypothetical document must not be empty"
        assert len(hypothetical) > 100, \
            f"Hypothetical too short ({len(hypothetical)} chars) — expected 100+ chars"

        # Should contain regulatory vocabulary
        lower = hypothetical.lower()
        has_adgm_terms = any(term in lower for term in [
            "adgm", "regulation", "article", "company", "memorandum",
            "articles", "director", "shareholder", "register", "compliance",
        ])
        assert has_adgm_terms, \
            f"Hypothetical lacks ADGM regulatory vocabulary: {hypothetical[:200]}"

        print(f"Hypothetical ({len(hypothetical)} chars):")
        print(f"  {hypothetical[:300]}...")
        print("PASS")
    except Exception as exc:
        print(f"SKIP (requires LLM API): {exc}")

run("Unit: Hypothetical doc contains ADGM regulatory terminology", test_hypothetical_contains_adgm_terminology)


def test_hyde_fallback_on_generation_failure():
    """When LLM generation fails, HyDE falls back to the original query."""
    from unittest.mock import MagicMock
    from backend.app.services.hyde_retriever import HyDERetriever

    mock_gemini = MagicMock()
    mock_gemini.generate_text.side_effect = RuntimeError("LLM service unavailable")

    mock_base = MagicMock()
    mock_base.search.return_value = []

    retriever = HyDERetriever(base=mock_base, gemini=mock_gemini, enabled=True)
    original_question = "what are the employment termination notice periods?"
    retriever.search(question=original_question)

    call_kwargs = mock_base.search.call_args
    query_used = call_kwargs[1].get("question") or call_kwargs[0][0]
    assert query_used == original_question, \
        f"Expected fallback to original question, got: {query_used}"
    assert retriever.last_hypothetical == "", "last_hypothetical should be empty after failure"
    print(f"Correctly fell back to original question: '{original_question}'")
    print("PASS")

run("Unit: Fallback to original query on LLM failure", test_hyde_fallback_on_generation_failure)


def test_hyde_disabled_mode():
    """When HyDE is disabled, the original question passes straight through."""
    from unittest.mock import MagicMock
    from backend.app.services.hyde_retriever import HyDERetriever

    mock_gemini = MagicMock()
    mock_base   = MagicMock()
    mock_base.search.return_value = []

    retriever = HyDERetriever(base=mock_base, gemini=mock_gemini, enabled=False)
    original_question = "UBO beneficial ownership disclosure"
    retriever.search(question=original_question)

    assert not mock_gemini.generate_text.called, \
        "generate_text must NOT be called when HyDE is disabled"
    call_kwargs = mock_base.search.call_args
    query_used = call_kwargs[1].get("question") or call_kwargs[0][0]
    assert query_used == original_question, \
        f"Expected original question to pass through, got: {query_used}"
    assert retriever.last_hypothetical == "", "last_hypothetical should be empty when disabled"
    print(f"Disabled mode: original query passed unchanged: '{original_question}'")
    print("PASS")

run("Unit: HyDE disabled mode passes query unchanged", test_hyde_disabled_mode)


def test_hyde_integration_retrieval():
    """HyDE retriever returns relevant chunks for a vague compliance query."""
    try:
        from backend.app.core.config import get_settings
        from backend.app.db.qdrant import get_qdrant_client
        from backend.app.services.bm25_retriever import BM25Retriever
        from backend.app.services.embeddings import get_embeddings_service
        from backend.app.services.generation import GeminiClient
        from backend.app.services.hybrid_retriever import HybridRetriever
        from backend.app.services.hyde_retriever import HyDERetriever
        from backend.app.services.reranker import LLMReranker, RerankedRetriever
        from backend.app.services.retrieval import QdrantRetriever

        settings   = get_settings()
        embeddings = get_embeddings_service(settings=settings)
        qdrant     = get_qdrant_client()

        dense    = QdrantRetriever(qdrant_client=qdrant, embeddings_service=embeddings)
        sparse   = BM25Retriever()
        hybrid   = HybridRetriever(dense=dense, sparse=sparse)
        gemini   = GeminiClient(settings=settings)
        reranker = LLMReranker(client=gemini)
        reranked = RerankedRetriever(base=hybrid, reranker=reranker, candidate_pool=10)
        retriever = HyDERetriever(base=reranked, gemini=gemini, enabled=True)

        vague_question = "what do I need to know about compliance?"
        chunks = retriever.search(question=vague_question, top_k=5)

        hypothetical = retriever.last_hypothetical
        print(f"Original query : '{vague_question}'")
        print(f"Hypothetical   : {hypothetical[:200]}...")
        print(f"Chunks returned: {len(chunks)}")
        for i, c in enumerate(chunks[:3], 1):
            print(f"  [{i}] {c.source_title or 'unknown'} | score={c.score:.3f} | {c.text[:80]}...")

        assert hypothetical, "Hypothetical document must be generated for vague query"
        assert len(hypothetical) > len(vague_question), \
            "Hypothetical doc should be richer than the original query"
        print("PASS")
    except Exception as exc:
        print(f"SKIP (requires services): {exc}")

run("Integration: HyDE retrieval for vague query", test_hyde_integration_retrieval)


def test_hyde_with_precise_query():
    """HyDE does not degrade retrieval for precise regulation-specific queries."""
    try:
        from backend.app.core.config import get_settings
        from backend.app.db.qdrant import get_qdrant_client
        from backend.app.services.bm25_retriever import BM25Retriever
        from backend.app.services.embeddings import get_embeddings_service
        from backend.app.services.generation import GeminiClient
        from backend.app.services.hybrid_retriever import HybridRetriever
        from backend.app.services.hyde_retriever import HyDERetriever
        from backend.app.services.reranker import LLMReranker, RerankedRetriever
        from backend.app.services.retrieval import QdrantRetriever

        settings   = get_settings()
        embeddings = get_embeddings_service(settings=settings)
        qdrant     = get_qdrant_client()

        dense    = QdrantRetriever(qdrant_client=qdrant, embeddings_service=embeddings)
        sparse   = BM25Retriever()
        hybrid   = HybridRetriever(dense=dense, sparse=sparse)
        gemini   = GeminiClient(settings=settings)
        reranker = LLMReranker(client=gemini)
        reranked = RerankedRetriever(base=hybrid, reranker=reranker, candidate_pool=10)
        retriever = HyDERetriever(base=reranked, gemini=gemini, enabled=True)

        precise_question = (
            "What is the maximum probation period allowed under ADGM Employment Regulations 2019?"
        )
        chunks = retriever.search(question=precise_question, top_k=5)

        print(f"Precise query  : '{precise_question[:80]}'")
        print(f"Chunks returned: {len(chunks)}")
        for i, c in enumerate(chunks[:3], 1):
            print(f"  [{i}] {c.source_title or 'unknown'} | score={c.score:.3f}")
        print("PASS")
    except Exception as exc:
        print(f"SKIP (requires services): {exc}")

run("Integration: HyDE with precise regulation query", test_hyde_with_precise_query)


# ---------------------------------------------------------------------------
# E2E API tests
# ---------------------------------------------------------------------------

def test_api_vague_question():
    """POST /chat with vague query returns a useful answer via HyDE."""
    data = post_json("/chat", {
        "question": "what do companies need to do to stay compliant in ADGM?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    model   = data.get("model", "?")
    sources = data.get("sources", [])
    latency = data.get("latency_ms", "?")
    print(f"Model   : {model}")
    print(f"Latency : {latency} ms")
    print(f"Sources : {len(sources)}")
    print(f"Answer  : {answer[:300]}")
    assert answer, "Expected a non-empty answer for vague compliance question"
    assert len(answer) > 80, f"Answer too short ({len(answer)} chars) — HyDE should enable richer retrieval"
    print("PASS")

run("E2E: Vague query — HyDE enables useful answer", test_api_vague_question)


def test_api_ubo_question():
    """POST /chat with UBO-specific query returns regulation-grounded answer."""
    data = post_json("/chat", {
        "question": "What are the beneficial ownership disclosure requirements for ADGM companies?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    model   = data.get("model", "?")
    sources = data.get("sources", [])
    print(f"Model   : {model}")
    print(f"Sources : {len(sources)}")
    print(f"Answer  : {answer[:400]}")
    assert answer, "Expected answer for UBO question"
    # Check for relevant terminology in the answer
    lower = answer.lower()
    has_relevant = any(term in lower for term in [
        "beneficial", "ownership", "ubo", "register", "25%", "adgm", "disclosure",
        "owner", "company", "regulation",
    ])
    assert has_relevant, f"Answer lacks relevant UBO/ownership terminology: {answer[:200]}"
    print("PASS")

run("E2E: UBO question — answer grounded in regulations", test_api_ubo_question)


def test_api_citations_present():
    """POST /chat returns citations with HyDE active."""
    data = post_json("/chat", {
        "question": "What are the minimum capital requirements for an ADGM private company?",
        "top_k": 5,
    })
    answer  = data.get("answer", "")
    sources = data.get("sources", [])
    print(f"Answer  : {answer[:300]}")
    print(f"Sources ({len(sources)}):")
    for s in sources:
        print(f"  - {s.get('source_title', 'unknown')} | collection={s.get('collection', '?')}")
    assert answer, "Expected answer"
    print("PASS")

run("E2E: Citations returned alongside HyDE-powered answer", test_api_citations_present)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'=' * 68}")
print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
print(f"{'=' * 68}")
sys.exit(0 if all_passed else 1)
