"""Hybrid retriever: dense (Qdrant) + sparse (BM25) fused via Reciprocal Rank Fusion.

Purpose
-------
Legal compliance documents require both:

* **Semantic matching** — understanding that "beneficial ownership disclosure"
  and "UBO requirements" mean the same thing.
* **Exact-term matching** — finding chunks that literally contain "Article 15",
  "25% threshold", "AoA", "MoA" regardless of surrounding context.

Dense-only retrieval misses precise legal citations.  BM25-only retrieval
misses paraphrased or concept-level queries.  Hybrid search covers both.

Fusion Algorithm — Reciprocal Rank Fusion (RRF)
-----------------------------------------------
RRF is the industry-standard algorithm for combining heterogeneous ranked
lists.  It is robust, parameter-stable, and does not require score
normalisation across retrievers.

    RRF(d) = Σᵢ  weight_i / (k + rank_i(d))

where k=60 is a stability constant that dampens the impact of very high ranks.
Chunks appearing in both lists accumulate contributions from both terms; chunks
unique to one list still appear if their within-list rank is high enough.

Architecture Integration
------------------------
* Phase 6: replaces ``QdrantRetriever`` as the retriever in ``BaselineRAGPipeline``.
* Phase 7 (re-ranking): ``HybridRetriever`` produces the top-30 candidate pool;
  a cross-encoder re-ranker then refines to top-5.
* Phase 8 (LangGraph): this class is wrapped as a single retrieval tool node.

The interface (``search(question, collections, top_k) → list[RetrievedChunk]``)
is identical to ``QdrantRetriever`` so no changes are needed in
``BaselineRAGPipeline`` or the endpoint.
"""

from __future__ import annotations

import logging

from backend.app.schemas.rag import RetrievedChunk
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.retrieval import DEFAULT_RETRIEVAL_COLLECTIONS, QdrantRetriever

logger = logging.getLogger(__name__)

# ── RRF hyper-parameters ───────────────────────────────────────────────────────

_RRF_K: int = 60
"""Stability constant.  k=60 is the empirically validated default from the
original RRF paper (Cormack et al., 2009).  Higher k → less aggressive
promotion of top-ranked items."""

_DENSE_WEIGHT: float = 0.7
"""Dense retriever contribution weight.  Higher because semantic matching is
the primary quality signal for most compliance questions."""

_SPARSE_WEIGHT: float = 0.3
"""BM25 contribution weight.  Lower but critical for exact legal-term recall."""

_CANDIDATE_MULTIPLIER: int = 4
"""Each retriever fetches this many times more candidates than top_k before
fusion.  Larger pools produce better RRF rankings at marginal latency cost."""


class HybridRetriever:
    """Combines Qdrant dense search and BM25 sparse search via RRF.

    Parameters
    ----------
    dense:
        ``QdrantRetriever`` for semantic vector search.
    sparse:
        ``BM25Retriever`` for exact-term matching.
    dense_weight:
        RRF weight for the dense list (default 0.7).
    sparse_weight:
        RRF weight for the sparse list (default 0.3).
    rrf_k:
        RRF stability constant (default 60).
    """

    def __init__(
        self,
        dense: QdrantRetriever,
        sparse: BM25Retriever,
        dense_weight: float = _DENSE_WEIGHT,
        sparse_weight: float = _SPARSE_WEIGHT,
        rrf_k: int = _RRF_K,
    ) -> None:
        self._dense = dense
        self._sparse = sparse
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight
        self._rrf_k = rrf_k

    def search(
        self,
        question: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Retrieve the top-K chunks using hybrid dense+sparse search.

        Steps
        -----
        1. Run dense (Qdrant) and sparse (BM25) retrievers independently,
           each fetching ``top_k × _CANDIDATE_MULTIPLIER`` candidates.
        2. Fuse both ranked lists using RRF with per-source weights.
        3. Return the top-K results, each carrying its RRF score.
        """
        target = collections or list(DEFAULT_RETRIEVAL_COLLECTIONS)
        candidate_pool = top_k * _CANDIDATE_MULTIPLIER

        dense_results = self._dense.search(question, target, candidate_pool)
        sparse_results = self._sparse.search(question, target, candidate_pool)

        fused = _rrf_fuse(
            dense_results,
            sparse_results,
            k=self._rrf_k,
            dense_weight=self._dense_weight,
            sparse_weight=self._sparse_weight,
        )

        logger.info(
            "Hybrid search — dense=%d  sparse=%d  fused=%d  → top_k=%d | %.60s…",
            len(dense_results),
            len(sparse_results),
            len(fused),
            top_k,
            question,
        )

        return fused[:top_k]


# ── RRF implementation ─────────────────────────────────────────────────────────

def _rrf_fuse(
    dense: list[RetrievedChunk],
    sparse: list[RetrievedChunk],
    k: int,
    dense_weight: float,
    sparse_weight: float,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion of two ranked lists.

    Each chunk accumulates a weighted RRF score from every list it appears in.
    Chunks exclusive to one list still contribute their single-list score.
    The returned list is sorted by RRF score descending; each chunk's
    ``score`` field is set to its final RRF score for transparency.

    Parameters
    ----------
    dense:
        Ranked list from the Qdrant dense retriever.
    sparse:
        Ranked list from the BM25 sparse retriever.
    k:
        RRF stability constant.
    dense_weight / sparse_weight:
        Per-list multipliers applied before summing.
    """
    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievedChunk] = {}

    for rank, chunk in enumerate(dense):
        rrf_scores[chunk.chunk_id] = (
            rrf_scores.get(chunk.chunk_id, 0.0)
            + dense_weight / (k + rank + 1)
        )
        chunk_map[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(sparse):
        rrf_scores[chunk.chunk_id] = (
            rrf_scores.get(chunk.chunk_id, 0.0)
            + sparse_weight / (k + rank + 1)
        )
        # Prefer dense chunk metadata when both retrievers return the same id
        chunk_map.setdefault(chunk.chunk_id, chunk)

    sorted_ids = sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True)

    return [
        chunk_map[cid].model_copy(update={"score": round(rrf_scores[cid], 6)})
        for cid in sorted_ids
    ]
