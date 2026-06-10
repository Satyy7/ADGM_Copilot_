"""BM25 sparse retriever for exact-term matching on ADGM regulatory text.

Purpose
-------
Legal and compliance documents contain precise terminology — regulation
numbers, article references, acronyms like "UBO", "AoA", "MoA" — that dense
vector search handles poorly when no semantically similar chunk happens to
exist.  BM25 (Okapi BM25) scores by exact token overlap, complementing dense
retrieval for these cases.

Architecture Integration
------------------------
* Phase 6: used as the sparse arm of ``HybridRetriever``.
* Phase 7+: the BM25 results feed into the re-ranker alongside dense results.
* Phase 8 (LangGraph): wrapped as a tool node callable from any agent.

The index is built once at startup from ``chunks.jsonl`` and held in memory.
With ~170 chunks the memory footprint is negligible (<5 MB).  For larger
knowledge bases the index can be serialised with ``pickle`` and loaded lazily.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from rank_bm25 import BM25Okapi

from backend.app.schemas.rag import RetrievedChunk
from backend.app.schemas.source import KnowledgeChunk

logger = logging.getLogger(__name__)

DEFAULT_CHUNKS_PATH: Path = Path("data/processed/chunks.jsonl")

# Per-collection candidate multiplier — fetch more than top_k before the
# global cross-collection merge so short collections are not under-represented.
_PER_COLLECTION_MULTIPLIER: int = 3


def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25 indexing.

    Uses a regex that preserves:
    * Hyphenated legal terms: ``non-disclosure``, ``co-director``
    * Decimal references: ``Article-15.2``, ``Rule-6A``
    * Numbers and percentages: ``25``, ``100``
    * Acronyms: ``UBO``, ``AoA``, ``MoA``

    All tokens are lowercased for case-insensitive matching.
    """
    return re.findall(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*", text.lower())


class BM25Retriever:
    """In-memory BM25 sparse retriever built from ``chunks.jsonl``.

    Builds one ``BM25Okapi`` index per Qdrant collection so that collection-
    level term frequencies are accurate.  Scores are normalised to [0, 1]
    within each collection for consistency with cosine similarity scores from
    the dense retriever.

    Parameters
    ----------
    chunks_path:
        Path to the ``chunks.jsonl`` produced by ``ingest_knowledge_base.py``.
        Defaults to ``data/processed/chunks.jsonl`` relative to CWD.
    """

    def __init__(self, chunks_path: Path | str = DEFAULT_CHUNKS_PATH) -> None:
        path = Path(chunks_path)
        if not path.exists():
            raise FileNotFoundError(
                f"BM25 index source not found: {path}. "
                "Run ingest_knowledge_base.py first."
            )

        collection_chunks: dict[str, list[KnowledgeChunk]] = defaultdict(list)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    chunk = KnowledgeChunk.model_validate_json(line)
                    collection_chunks[chunk.collection].append(chunk)

        self._chunks: dict[str, list[KnowledgeChunk]] = dict(collection_chunks)
        self._indices: dict[str, BM25Okapi] = {}

        for collection, chunks in self._chunks.items():
            corpus = [_tokenize(c.text) for c in chunks]
            self._indices[collection] = BM25Okapi(corpus)
            logger.info(
                "BM25 index ready — collection=%s  docs=%d", collection, len(chunks)
            )

    # ── Public API ─────────────────────────────────────────────────────────────

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the top-K BM25-scored chunks across target collections.

        Parameters
        ----------
        question:
            Raw user question — tokenized identically to indexed chunks.
        collections:
            Collections to search.  Defaults to all indexed collections.
        top_k:
            Final number of results returned after cross-collection merge.
        """
        target = collections or list(self._indices.keys())
        query_tokens = _tokenize(question)

        if not query_tokens:
            return []

        all_results: list[RetrievedChunk] = []
        per_collection_limit = max(top_k, top_k * _PER_COLLECTION_MULTIPLIER)

        for collection in target:
            if collection not in self._indices:
                logger.debug("BM25: no index for collection '%s', skipping.", collection)
                continue

            scores = self._indices[collection].get_scores(query_tokens)
            chunks = self._chunks[collection]

            # Rank by score descending, take candidates
            ranked = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:per_collection_limit]

            max_score = scores[ranked[0]] if ranked else 0.0
            if max_score <= 0:
                continue  # no term overlap in this collection

            for idx in ranked:
                if scores[idx] <= 0:
                    break  # sorted — all remaining are also zero
                chunk = chunks[idx]
                normalised = round(float(scores[idx]) / max_score, 6)
                all_results.append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        collection=chunk.collection,
                        text=chunk.text,
                        score=normalised,
                        source_title=chunk.metadata.get("source_title"),
                        source_url=(
                            chunk.metadata.get("canonical_url")
                            or chunk.metadata.get("source_url")
                        ),
                        rule_reference=chunk.metadata.get("rule_reference"),
                        page_number=chunk.metadata.get("page_number"),
                        heading=chunk.metadata.get("heading"),
                        authority=chunk.metadata.get("authority"),
                    )
                )

        # Final cross-collection sort, deduplicate, return top_k
        seen: set[str] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in sorted(all_results, key=lambda c: c.score, reverse=True):
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                deduped.append(chunk)

        return deduped[:top_k]
