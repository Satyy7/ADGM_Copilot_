"""LLM-based listwise re-ranker for ADGM compliance retrieval (Phase 7).

Purpose
-------
Hybrid search (Phase 6) produces a candidate pool ranked by Reciprocal Rank
Fusion of dense and sparse scores.  RRF is excellent at combining ranked
lists, but it is a *lexical and statistical* signal — it does not understand
whether a chunk actually *answers* the question.

A cross-encoder re-ranker reads both the question and each candidate chunk
together and scores contextual relevance directly.  This two-stage pattern
(cheap broad retrieval → expensive accurate re-ranking) is standard in
production retrieval systems.

Why LLM-based rather than a dedicated cross-encoder model?
----------------------------------------------------------
* Zero new dependencies — reuses the existing Gemini/Groq client.
* Legal context awareness — the LLM understands ADGM-specific terminology
  (UBO, AoA, MoA, Article references) far better than a generic MS-MARCO
  cross-encoder trained on web search queries.
* Listwise approach — a single API call ranks all candidates at once,
  avoiding the N API calls that pointwise scoring would require.
* Graceful degradation — if the LLM returns an unparseable response, the
  re-ranker falls back to the original hybrid order transparently.

Architecture Integration
------------------------
* Phase 7: ``RerankedRetriever`` wraps ``HybridRetriever`` and satisfies the
  ``Retriever`` Protocol — drop-in replacement in ``_get_pipeline()``.
* Phase 8 (LangGraph): ``RerankedRetriever`` becomes the retrieval tool node
  in the state graph; no interface change required.
* Phase 9 (Compliance Review Agent): sub-agents call the same
  ``RerankedRetriever`` for evidence gathering.

Retrieval stack after Phase 7
------------------------------
  Query
    └─► QdrantRetriever (dense, top-20 candidates)  ─┐
    └─► BM25Retriever   (sparse, top-20 candidates)  ─┤  HybridRetriever
                                                       └─► RRF fusion (top-20)
                                                            └─► LLMReranker
                                                                 └─► top-5 answer
"""

from __future__ import annotations

import logging
import re

from backend.app.schemas.rag import RetrievedChunk
from backend.app.services.retrieval import Retriever

logger = logging.getLogger(__name__)

# ── Re-ranking prompt ──────────────────────────────────────────────────────────

_RERANK_PROMPT: str = """\
You are ranking regulatory document passages for a compliance question.

Task: Given the question below and {n} numbered passages, output the passage \
numbers in order from MOST relevant to LEAST relevant.

Rules:
- Return ONLY a JSON array of all {n} numbers. Example: [3, 1, 5, 2, 4]
- Include every number from 1 to {n} exactly once.
- No explanation, no other text.

Question: {question}

Passages:
{passages}

Ranking:"""

# Characters of each chunk's text included in the re-ranking prompt.
# 300 chars is enough context for the LLM to judge relevance without
# overflowing the prompt for a 20-candidate pool.
_PASSAGE_PREVIEW_CHARS: int = 300


class LLMReranker:
    """Re-ranks a candidate list using a single listwise LLM call.

    The LLM receives the question and all candidate passages and returns
    a ranked order.  One API call regardless of candidate pool size.

    Parameters
    ----------
    client:
        ``GeminiClient`` instance (already has Groq fallback built in).
    """

    def __init__(self, client: object) -> None:
        # typed as object to avoid a circular import; actual type is GeminiClient
        self._client = client

    def rerank(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Re-rank ``chunks`` by relevance to ``question``, return top ``top_k``.

        Falls back to original hybrid order if the LLM response cannot be parsed.
        """
        if len(chunks) <= top_k:
            return chunks  # nothing to re-rank

        passages = "\n".join(
            f"[{i + 1}] ({c.collection}) {c.text[:_PASSAGE_PREVIEW_CHARS].strip()}"
            for i, c in enumerate(chunks)
        )
        prompt = _RERANK_PROMPT.format(
            n=len(chunks),
            question=question,
            passages=passages,
        )

        try:
            raw = self._client.generate_text(prompt)  # type: ignore[union-attr]
            ranked = _parse_ranking(raw, total=len(chunks))
            reranked = [chunks[i - 1] for i in ranked]
            logger.info(
                "Re-ranked %d → top-%d | top chunk_id=%s score=%.5f",
                len(chunks),
                top_k,
                reranked[0].chunk_id if reranked else "?",
                reranked[0].score if reranked else 0.0,
            )
            return reranked[:top_k]

        except Exception as exc:
            logger.warning(
                "Re-ranking failed (%s: %s), falling back to hybrid order.",
                type(exc).__name__,
                str(exc)[:120],
            )
            return chunks[:top_k]


class RerankedRetriever:
    """Wraps any ``Retriever`` with an LLM re-ranking post-processing step.

    Fetches a larger candidate pool from the base retriever (default: 20),
    then narrows it to ``top_k`` using ``LLMReranker``.  Satisfies the
    ``Retriever`` Protocol — drop-in replacement wherever a retriever is expected.

    Parameters
    ----------
    base:
        Any object satisfying the ``Retriever`` Protocol (e.g. ``HybridRetriever``).
    reranker:
        ``LLMReranker`` instance.
    candidate_pool:
        Number of candidates to fetch before re-ranking.
        Should be >= top_k; higher values improve recall at the cost of a
        slightly longer re-ranking prompt.
    """

    def __init__(
        self,
        base: Retriever,
        reranker: LLMReranker,
        candidate_pool: int = 20,
    ) -> None:
        self._base = base
        self._reranker = reranker
        self._candidate_pool = candidate_pool

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Retrieve candidates via hybrid search, then re-rank to top ``top_k``."""
        pool_size = max(self._candidate_pool, top_k)
        candidates = self._base.search(question, collections, top_k=pool_size)
        return self._reranker.rerank(question, candidates, top_k)


# ── Parsing helper ─────────────────────────────────────────────────────────────

def _parse_ranking(raw: str, total: int) -> list[int]:
    """Parse an LLM ranking response into a 1-based index list.

    Handles all common LLM output formats:
    * ``[3, 1, 5, 2, 4]``        — clean JSON array
    * ``3, 1, 5, 2, 4``          — plain comma-separated
    * ``Ranking: [3,1,5,2,4]``   — prefixed
    * ``[3, 1, 5]``              — partial list (missing indices appended)

    Any number outside [1, total] is silently discarded.  Missing indices are
    appended at the end in their original order so the output always has
    exactly ``total`` entries.
    """
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    valid_in_order: list[int] = []
    seen: set[int] = set()
    for n in nums:
        if 1 <= n <= total and n not in seen:
            seen.add(n)
            valid_in_order.append(n)

    # Append any indices the LLM omitted, preserving original relative order
    for i in range(1, total + 1):
        if i not in seen:
            valid_in_order.append(i)

    return valid_in_order
