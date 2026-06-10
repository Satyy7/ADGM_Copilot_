"""Format-aware chunking for ADGM knowledge sources."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from backend.app.schemas.source import KnowledgeChunk, NormalizedDocument, NormalizedSection


def token_count(text: str) -> int:
    """Approximate token count using whitespace splitting."""

    return len(text.split())


def chunk_hash(text: str, metadata: dict) -> str:
    """Build a stable chunk hash from text and source metadata."""

    basis = f"{metadata.get('source_id')}|{metadata.get('chunk_index')}|{text}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def split_by_tokens(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into overlapping token windows."""

    tokens = text.split()
    if len(tokens) <= max_tokens:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(" ".join(tokens[start:end]))
        if end == len(tokens):
            break
        start = max(0, end - overlap_tokens)
    return chunks


def split_rulebook_text(text: str) -> list[str]:
    """Split legal/rulebook content around numbered rules and articles."""

    pattern = re.compile(
        r"(?=(?:^|\s)(?:Rule|Article|Section|Part)\s+\d+(?:[A-Za-z]|\.\d+)*)",
        re.IGNORECASE,
    )
    parts = [part.strip() for part in pattern.split(text) if part.strip()]
    return parts or [text]


def chunk_settings(document: NormalizedDocument) -> tuple[int, int]:
    """Return max and overlap token settings for a document type."""

    if document.source.collection == "regulations":
        return 650, 80
    if document.source.collection == "templates":
        return 700, 90
    if document.source.collection == "checklists":
        return 850, 120
    return 900, 120


def section_units(document: NormalizedDocument, section: NormalizedSection) -> list[str]:
    """Return semantic units for a section before windowing."""

    if document.source.collection == "regulations":
        return split_rulebook_text(section.text)
    if document.source.collection == "checklists":
        return split_checklist_text(section.text)
    if document.source.collection == "templates":
        return split_template_text(section.text)
    return [section.text]


def split_checklist_text(text: str) -> list[str]:
    """Split checklist text on numbered/bulleted requirement boundaries."""

    pattern = re.compile(r"(?=(?:^|\s)(?:\d+\.\s+|[A-Z]\.\s+|Requirement\s+\d+))")
    parts = [part.strip() for part in pattern.split(text) if part.strip()]
    return parts or [text]


def split_template_text(text: str) -> list[str]:
    """Split template text on clause-like boundaries when visible."""

    pattern = re.compile(r"(?=(?:^|\s)(?:\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z]|Clause\s+\d+))")
    parts = [part.strip() for part in pattern.split(text) if part.strip()]
    return parts or [text]


def build_chunk_metadata(
    document: NormalizedDocument,
    section: NormalizedSection,
    chunk_index: int,
) -> dict:
    """Build citation-grade metadata for one chunk."""

    source = document.source
    return {
        "source_id": source.source_id,
        "source_url": str(source.url),
        "canonical_url": str(source.url).split("?")[0],
        "source_title": document.title,
        "source_format": source.source_format,
        "collection": source.collection,
        "category": source.category,
        "document_type": source.document_type,
        "authority": source.authority,
        "jurisdiction": source.jurisdiction,
        "official_source": source.official_source,
        "section_path": section.section_path,
        "heading": section.heading,
        "page_number": section.page_number,
        "rule_reference": infer_rule_reference(section.text),
        "template_type": source.document_type if source.collection == "templates" else None,
        "downloaded_path": document.downloaded_path,
        "file_hash": document.file_hash,
        "chunk_index": chunk_index,
        "chunked_at": datetime.now(UTC).isoformat(),
    }


def infer_rule_reference(text: str) -> str | None:
    """Extract a likely rule/article reference from a text chunk."""

    match = re.search(
        r"\b(?:Rule|Article|Section|Part)\s+\d+(?:[A-Za-z]|\.\d+)*\b",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else None


def chunk_document(document: NormalizedDocument) -> list[KnowledgeChunk]:
    """Chunk a normalized document into retrieval-ready records."""

    max_tokens, overlap_tokens = chunk_settings(document)
    chunks: list[KnowledgeChunk] = []

    for section in document.sections:
        for unit in section_units(document, section):
            for text_window in split_by_tokens(unit, max_tokens, overlap_tokens):
                if token_count(text_window) < 8:
                    continue

                chunk_index = len(chunks)
                metadata = build_chunk_metadata(document, section, chunk_index)
                metadata["chunk_hash"] = chunk_hash(text_window, metadata)
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{document.source.source_id}-{chunk_index:04d}",
                        source_id=document.source.source_id,
                        collection=document.source.collection,
                        text=text_window,
                        metadata=metadata,
                    )
                )

    return chunks

