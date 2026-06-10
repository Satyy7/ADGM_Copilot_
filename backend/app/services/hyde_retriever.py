"""HyDE — Hypothetical Document Embeddings retriever (Phase 13).

Theory
------
Vague or short compliance queries (e.g. "what are the UBO requirements?") embed
poorly against regulatory chunks because the query lacks the dense legal
vocabulary that characterises those chunks.

HyDE fixes this by having the LLM first draft a *hypothetical* regulatory
excerpt that *would* answer the question — rich with article references,
thresholds, and formal ADGM terminology.  That hypothetical document is then
used as the retrieval query instead of the raw question.  Its embedding lands
much closer to the real regulatory chunks in vector space.

Algorithm
---------
1. LLM generates a 150-250 word regulatory excerpt for the query.
2. The excerpt is passed to the base retriever stack in place of the query.
3. Results are returned unchanged.

Fallback: if HyDE generation fails for any reason the original question is
used directly — the retriever never blocks.

Stack position after Phase 13
------------------------------
    HyDERetriever               ← Phase 13 (this file)
        └── RerankedRetriever   ← Phase 7
                └── HybridRetriever (RRF, k=60)  ← Phase 6
                        ├── QdrantRetriever (dense cosine)  ← Phase 5
                        └── BM25Retriever   (sparse Okapi)  ← Phase 6

Protocol compliance
-------------------
``HyDERetriever`` satisfies the ``Retriever`` Protocol defined in
``backend.app.services.retrieval`` — drop-in replacement at any stack level.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.app.schemas.rag import RetrievedChunk

if TYPE_CHECKING:
    from backend.app.services.retrieval import Retriever

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HyDE generation prompt
# ---------------------------------------------------------------------------

_HYDE_PROMPT = """\
You are a senior ADGM compliance specialist drafting regulatory guidance.
Write a precise, detailed regulatory excerpt that directly answers the question below.

Requirements:
- Use formal ADGM regulatory language and terminology
- Reference specific articles, sections, and regulation names where applicable
  (e.g. "Article 12 of the Companies Regulations 2020", "ADGM Employment Regulations 2019")
- Include specific thresholds, timeframes, percentages, and obligations
- Write 150-200 words as if from an official ADGM guidance document
- Do NOT include disclaimers, "According to..." preambles, or personal pronouns

Question: {question}

Regulatory excerpt:"""


class HyDERetriever:
    """Wrap any ``Retriever`` with Hypothetical Document Embeddings.

    Parameters
    ----------
    base:
        Any ``Retriever``-protocol object (typically ``RerankedRetriever``).
    gemini:
        ``GeminiClient`` instance used for hypothetical document generation.
    enabled:
        When ``False``, passes the original question straight to the base
        retriever — useful for A/B comparison or disabling HyDE at runtime.
    """

    def __init__(self, base: "Retriever", gemini: object, enabled: bool = True) -> None:
        self._base    = base
        self._gemini  = gemini
        self._enabled = enabled
        self._last_hypothetical: str = ""   # inspectable in tests / logs

    # ── Retriever Protocol ─────────────────────────────────────────────────────

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Embed a hypothetical answer to the question, retrieve matching chunks.

        Falls back to the original ``question`` if HyDE generation fails.
        """
        if not self._enabled:
            self._last_hypothetical = ""
            return self._base.search(question=question, collections=collections, top_k=top_k)

        hypothetical = self._generate_hypothetical(question)
        retrieval_query = hypothetical if hypothetical else question

        logger.info(
            "HyDE query (first 120 chars): %.120s…",
            retrieval_query,
        )

        chunks = self._base.search(
            question=retrieval_query,
            collections=collections,
            top_k=top_k,
        )
        logger.info("HyDE search returned %d chunks.", len(chunks))
        return chunks

    # ── Inspection ─────────────────────────────────────────────────────────────

    @property
    def last_hypothetical(self) -> str:
        """The hypothetical document generated in the most recent search call.

        Empty string when ``enabled=False`` or after a generation failure.
        """
        return self._last_hypothetical

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── Internals ──────────────────────────────────────────────────────────────

    def _generate_hypothetical(self, question: str) -> str:
        """Generate a hypothetical regulatory document for ``question``.

        Returns the document text, or an empty string on failure (caller falls
        back to the original question).
        """
        prompt = _HYDE_PROMPT.format(question=question)
        try:
            doc: str = self._gemini.generate_text(prompt)  # type: ignore[union-attr]
            doc = doc.strip()
            self._last_hypothetical = doc
            logger.debug("HyDE hypothetical document (%d chars): %.200s…", len(doc), doc)
            return doc
        except Exception as exc:
            logger.warning(
                "HyDE generation failed (%s) — falling back to original query.", exc
            )
            self._last_hypothetical = ""
            return ""
