"""Embed chunks and index them into Qdrant collections.

Purpose
-------
This script is Phase 4's final step. It reads the ``chunks.jsonl`` produced
by ``ingest_knowledge_base.py``, generates Gemini embeddings for every chunk,
and upserts the resulting points into the five Qdrant collections:

    regulations | templates | guidance | checklists | historical_reviews

Each Qdrant point carries the full chunk payload (text + all citation-grade
metadata) so retrieval results are self-contained and need no back-joins.

Architecture Integration
------------------------
* Depends on ``EmbeddingsService`` (Phase 4, this PR).
* Depends on ``get_qdrant_client()`` and collection constants (Phase 3 / Phase 1).
* Output: populated Qdrant collections ready for Phase 5 baseline retrieval.
* Run once after ``ingest_knowledge_base.py`` whenever the knowledge base is
  refreshed. Use ``--collection`` to re-index a single collection.

Usage
-----
    python scripts/index_knowledge_base.py

    # Re-index only the regulations collection
    python scripts/index_knowledge_base.py --collection regulations

    # Dry-run: embed and report without writing to Qdrant
    python scripts/index_knowledge_base.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Generator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.core.config import get_settings
from backend.app.core.constants import QDRANT_COLLECTIONS
from backend.app.core.logging import configure_logging
from backend.app.db.qdrant import create_qdrant_client
from backend.app.schemas.source import KnowledgeChunk
from backend.app.services.embeddings import (
    EMBEDDING_DIMENSION,
    EmbeddingsService,
    get_embeddings_service,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_QDRANT_UPSERT_BATCH: int = 100
"""Points per Qdrant upsert call. Keeps individual HTTP payloads manageable."""

_EMBED_BATCH: int = 20
"""Texts per Gemini embedding call. Matches EmbeddingsService.EMBEDDING_BATCH_SIZE."""


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed ADGM knowledge chunks and index them into Qdrant.",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/chunks.jsonl"),
        help="JSONL file produced by ingest_knowledge_base.py.",
    )
    parser.add_argument(
        "--collection",
        type=str,
        choices=list(QDRANT_COLLECTIONS),
        default=None,
        help="Index only this collection (omit to index all five).",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=_EMBED_BATCH,
        help="Texts per Gemini embedding call.",
    )
    parser.add_argument(
        "--upsert-batch-size",
        type=int,
        default=_QDRANT_UPSERT_BATCH,
        help="Points per Qdrant upsert call.",
    )
    parser.add_argument(
        "--recreate-collections",
        action="store_true",
        default=False,
        help="Delete and recreate Qdrant collections before indexing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Embed chunks but skip writing to Qdrant.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/processed/indexing_report.json"),
        help="Path for the JSON indexing report.",
    )
    return parser.parse_args()


# ── Helpers ────────────────────────────────────────────────────────────────────

def chunk_id_to_point_id(chunk_id: str) -> str:
    """Convert an arbitrary chunk_id string to a deterministic UUID string.

    Qdrant requires point IDs to be either uint64 or UUID. We derive a stable
    UUID from the chunk_id so the indexer is idempotent — re-indexing the same
    chunk always produces the same point ID and Qdrant will upsert (overwrite)
    rather than create a duplicate.
    """
    digest = hashlib.sha256(chunk_id.encode("utf-8")).digest()[:16]
    return str(uuid.UUID(bytes=digest))


def load_chunks_from_jsonl(path: Path) -> list[KnowledgeChunk]:
    """Read all KnowledgeChunk records from a JSONL file."""
    chunks: list[KnowledgeChunk] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(KnowledgeChunk.model_validate(json.loads(line)))
            except Exception as exc:
                logger.warning("Skipping malformed line %d: %s", line_num, exc)
    return chunks


def group_by_collection(
    chunks: list[KnowledgeChunk],
    target_collection: str | None,
) -> dict[str, list[KnowledgeChunk]]:
    """Group chunks by Qdrant collection, optionally filtered to one collection."""
    grouped: dict[str, list[KnowledgeChunk]] = defaultdict(list)
    for chunk in chunks:
        if target_collection is None or chunk.collection == target_collection:
            grouped[chunk.collection].append(chunk)
    return dict(grouped)


def iter_batches(
    items: list,
    batch_size: int,
) -> Generator[list, None, None]:
    """Yield successive fixed-size batches from a list."""
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def build_point_payload(chunk: KnowledgeChunk) -> dict:
    """Build the Qdrant point payload from a KnowledgeChunk.

    The payload is the source of truth for retrieval results — it includes
    both the raw text (returned to the LLM as context) and all citation-grade
    metadata (used to build source citations in responses).
    """
    return {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "collection": chunk.collection,
        "text": chunk.text,
        **chunk.metadata,
    }


# ── Qdrant collection management ───────────────────────────────────────────────

def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    recreate: bool,
) -> None:
    """Create a Qdrant collection if it does not exist.

    When ``recreate=True`` the existing collection is deleted first. Use this
    flag when you want a clean slate after a schema or embedding model change.
    """
    existing = {c.name for c in client.get_collections().collections}

    if recreate and collection_name in existing:
        logger.info("Deleting existing collection '%s'.", collection_name)
        client.delete_collection(collection_name)
        existing.discard(collection_name)

    if collection_name not in existing:
        logger.info(
            "Creating Qdrant collection '%s' (dim=%d, distance=Cosine).",
            collection_name,
            EMBEDDING_DIMENSION,
        )
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
    else:
        logger.info("Collection '%s' already exists — upserting into it.", collection_name)


# ── Core indexing logic ────────────────────────────────────────────────────────

def index_collection(
    collection_name: str,
    chunks: list[KnowledgeChunk],
    embeddings_service: EmbeddingsService,
    qdrant_client: QdrantClient,
    embed_batch_size: int,
    upsert_batch_size: int,
    recreate: bool,
    dry_run: bool,
) -> dict:
    """Embed and index all chunks for one Qdrant collection.

    Returns a stats dict for the final report.
    """
    stats: dict = {
        "collection": collection_name,
        "total_chunks": len(chunks),
        "upserted": 0,
        "skipped_empty_vector": 0,
        "errors": 0,
    }

    if not chunks:
        logger.info("No chunks for collection '%s' — skipping.", collection_name)
        return stats

    logger.info(
        "Indexing collection '%s': %d chunks.",
        collection_name,
        len(chunks),
    )

    if not dry_run:
        ensure_collection(qdrant_client, collection_name, recreate=recreate)

    # Embed all chunks in batches
    all_pairs: list[tuple[KnowledgeChunk, list[float]]] = []
    for batch_num, batch in enumerate(iter_batches(chunks, embed_batch_size), 1):
        logger.debug(
            "[%s] Embedding batch %d (%d texts).",
            collection_name,
            batch_num,
            len(batch),
        )
        try:
            pairs = embeddings_service.embed_chunks(batch)
            all_pairs.extend(pairs)
        except Exception as exc:
            logger.error(
                "[%s] Embedding batch %d failed: %s — skipping batch.",
                collection_name,
                batch_num,
                exc,
            )
            stats["errors"] += len(batch)

    if not all_pairs:
        logger.warning("No embeddings produced for '%s'.", collection_name)
        return stats

    # Upsert into Qdrant in batches
    for upsert_batch in iter_batches(all_pairs, upsert_batch_size):
        points: list[PointStruct] = []
        for chunk, vector in upsert_batch:
            if not vector:
                logger.warning("Empty vector for chunk '%s' — skipping.", chunk.chunk_id)
                stats["skipped_empty_vector"] += 1
                continue
            points.append(
                PointStruct(
                    id=chunk_id_to_point_id(chunk.chunk_id),
                    vector=vector,
                    payload=build_point_payload(chunk),
                )
            )

        if points and not dry_run:
            try:
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True,
                )
                stats["upserted"] += len(points)
                logger.debug(
                    "[%s] Upserted %d points (running total: %d).",
                    collection_name,
                    len(points),
                    stats["upserted"],
                )
            except Exception as exc:
                logger.error(
                    "[%s] Qdrant upsert failed for batch: %s",
                    collection_name,
                    exc,
                )
                stats["errors"] += len(points)
        elif dry_run:
            stats["upserted"] += len(points)

    logger.info(
        "[%s] Done — upserted=%d, skipped=%d, errors=%d.",
        collection_name,
        stats["upserted"],
        stats["skipped_empty_vector"],
        stats["errors"],
    )
    return stats


# ── Report ─────────────────────────────────────────────────────────────────────

def save_report(report: dict, path: Path) -> None:
    """Write the indexing report as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Indexing report written to %s", path)


def print_summary(report: dict) -> None:
    """Print a human-readable summary to stdout."""
    print("\n" + "=" * 60)
    print("  ADGM Knowledge Base — Indexing Report")
    print("=" * 60)
    print(f"  Completed at : {report['completed_at']}")
    print(f"  Dry run      : {report['dry_run']}")
    print(f"  Chunks file  : {report['chunks_file']}")
    print()
    total_upserted = 0
    for stat in report["collections"]:
        status = "DRY-RUN" if report["dry_run"] else "INDEXED"
        print(
            f"  [{status}] {stat['collection']:<22} "
            f"chunks={stat['total_chunks']:>5}  "
            f"upserted={stat['upserted']:>5}  "
            f"errors={stat['errors']:>3}"
        )
        total_upserted += stat["upserted"]
    print()
    print(f"  Total points upserted : {total_upserted}")
    print("=" * 60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the knowledge-base indexing pipeline."""
    settings = get_settings()
    configure_logging(settings)
    args = parse_args()

    # ── Validate inputs ────────────────────────────────────────────────────────
    if not args.chunks.exists():
        logger.error(
            "Chunks file not found: %s\n"
            "Run ingest_knowledge_base.py first to generate it.",
            args.chunks,
        )
        sys.exit(1)

    # ── Load chunks ────────────────────────────────────────────────────────────
    logger.info("Loading chunks from %s …", args.chunks)
    all_chunks = load_chunks_from_jsonl(args.chunks)
    logger.info("Loaded %d total chunks.", len(all_chunks))

    grouped = group_by_collection(all_chunks, target_collection=args.collection)
    if not grouped:
        logger.error(
            "No chunks found for collection filter '%s'.",
            args.collection or "all",
        )
        sys.exit(1)

    target_names = sorted(grouped.keys())
    logger.info(
        "Collections to index: %s",
        ", ".join(f"{n}({len(grouped[n])})" for n in target_names),
    )

    # ── Initialise services ────────────────────────────────────────────────────
    embeddings_service = get_embeddings_service(settings=settings)
    qdrant_client = create_qdrant_client(settings=settings) if not args.dry_run else None  # type: ignore[assignment]

    if args.dry_run:
        logger.info("DRY RUN — embeddings will be generated but not written to Qdrant.")

    # ── Index each collection ──────────────────────────────────────────────────
    collection_stats: list[dict] = []
    for name in target_names:
        stats = index_collection(
            collection_name=name,
            chunks=grouped[name],
            embeddings_service=embeddings_service,
            qdrant_client=qdrant_client,  # type: ignore[arg-type]
            embed_batch_size=args.embed_batch_size,
            upsert_batch_size=args.upsert_batch_size,
            recreate=args.recreate_collections,
            dry_run=args.dry_run,
        )
        collection_stats.append(stats)

    # ── Report ─────────────────────────────────────────────────────────────────
    report = {
        "completed_at": datetime.now(UTC).isoformat(),
        "dry_run": args.dry_run,
        "chunks_file": str(args.chunks),
        "target_collection": args.collection,
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "collections": collection_stats,
    }
    save_report(report, args.report)
    print_summary(report)


if __name__ == "__main__":
    main()
