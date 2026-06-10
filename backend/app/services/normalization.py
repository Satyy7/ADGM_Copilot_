"""Normalization helpers for source documents and chunks."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from backend.app.schemas.source import KnowledgeChunk, NormalizedDocument


def write_json_model(model: BaseModel, path: Path) -> None:
    """Write one Pydantic model as pretty JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def write_jsonl_chunks(chunks: list[KnowledgeChunk], path: Path) -> None:
    """Write chunks to JSONL for inspection and later indexing."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(chunk.model_dump_json() + "\n")


def read_normalized_document(path: Path) -> NormalizedDocument:
    """Read a normalized document JSON file."""

    return NormalizedDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))

