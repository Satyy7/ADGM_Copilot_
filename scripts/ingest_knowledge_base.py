"""Download, normalize, and chunk official ADGM knowledge sources.

This script stops before embeddings/Qdrant indexing. Its output is a set of
auditable normalized JSON documents and a JSONL chunk file ready for retrieval
quality checks and later vector indexing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.source import KnowledgeChunk, SourceRecord
from backend.app.services.chunking import chunk_document
from backend.app.services.loaders import download_source, load_source_file, raw_file_extension
from backend.app.services.normalization import write_json_model, write_jsonl_chunks
from backend.app.services.source_registry import (
    extract_source_manifest,
    load_source_manifest,
    save_source_manifest,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-docx",
        type=Path,
        default=Path("Data Sources.docx"),
        help="Seed DOCX containing official source links.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/source_registry.json"),
        help="Source manifest path.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory for downloaded raw sources.",
    )
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=Path("data/processed/normalized"),
        help="Directory for normalized source JSON files.",
    )
    parser.add_argument(
        "--chunks-output",
        type=Path,
        default=Path("data/processed/chunks.jsonl"),
        help="JSONL output path for chunks.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("data/processed/ingestion_report.json"),
        help="JSON output path for ingestion QA summary.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use existing raw files instead of downloading sources.",
    )
    return parser.parse_args()


def ensure_manifest(source_docx: Path, manifest_path: Path) -> list[SourceRecord]:
    """Load or create the source manifest."""

    if manifest_path.exists():
        return load_source_manifest(manifest_path).sources

    manifest = extract_source_manifest(source_docx)
    save_source_manifest(manifest, manifest_path)
    return manifest.sources


def raw_path_for_source(source: SourceRecord, raw_dir: Path) -> Path:
    """Return the expected raw file path for one source."""

    return raw_dir / source.collection / f"{source.source_id}{raw_file_extension(source)}"


def process_source(
    source: SourceRecord,
    *,
    raw_dir: Path,
    normalized_dir: Path,
    skip_download: bool,
) -> list[KnowledgeChunk]:
    """Download if needed, normalize, chunk, and persist one source."""

    raw_path = raw_path_for_source(source, raw_dir)
    if not skip_download or not raw_path.exists():
        raw_path = download_source(source, raw_dir)

    normalized = load_source_file(source, raw_path)
    normalized_path = normalized_dir / source.collection / f"{source.source_id}.json"
    write_json_model(normalized, normalized_path)
    return chunk_document(normalized)


def main() -> None:
    """Run ingestion for all sources in the manifest."""

    args = parse_args()
    sources = ensure_manifest(args.source_docx, args.manifest)
    all_chunks: list[KnowledgeChunk] = []
    failures: list[str] = []

    for source in sources:
        try:
            chunks = process_source(
                source,
                raw_dir=args.raw_dir,
                normalized_dir=args.normalized_dir,
                skip_download=args.skip_download,
            )
            all_chunks.extend(chunks)
            print(
                f"OK {source.source_id} {source.collection} "
                f"{source.source_format}: {len(chunks)} chunks"
            )
        except Exception as exc:
            failures.append(f"{source.source_id} {source.url}: {exc}")
            print(f"FAILED {source.source_id}: {exc}")

    write_jsonl_chunks(all_chunks, args.chunks_output)
    write_ingestion_report(
        chunks=all_chunks,
        failures=failures,
        output_path=args.report_output,
    )
    print(f"Wrote {len(all_chunks)} chunks to {args.chunks_output}")
    print(f"Wrote ingestion report to {args.report_output}")

    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)


def write_ingestion_report(
    *,
    chunks: list[KnowledgeChunk],
    failures: list[str],
    output_path: Path,
) -> None:
    """Write a QA summary for the ingestion run."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_hashes = [chunk.metadata["chunk_hash"] for chunk in chunks]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_chunks": len(chunks),
        "total_sources": len({chunk.source_id for chunk in chunks}),
        "chunks_by_collection": dict(Counter(chunk.collection for chunk in chunks)),
        "chunks_by_format": dict(
            Counter(chunk.metadata["source_format"] for chunk in chunks)
        ),
        "empty_chunks": sum(1 for chunk in chunks if not chunk.text.strip()),
        "duplicate_chunk_hashes": len(chunk_hashes) - len(set(chunk_hashes)),
        "metadata_missing_required_fields": count_chunks_missing_metadata(chunks),
        "failures": failures,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def count_chunks_missing_metadata(chunks: list[KnowledgeChunk]) -> int:
    """Count chunks missing required retrieval/citation metadata."""

    required_fields = {
        "source_url",
        "source_title",
        "source_format",
        "collection",
        "document_type",
        "chunk_hash",
    }
    return sum(
        1
        for chunk in chunks
        if not required_fields.issubset(chunk.metadata.keys())
    )


if __name__ == "__main__":
    main()
