"""Schemas for source registry, normalized documents, and knowledge chunks."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, Field

SourceFormat = Literal["html", "pdf", "docx", "unknown"]
KnowledgeCollection = Literal[
    "regulations",
    "templates",
    "guidance",
    "checklists",
    "historical_reviews",
]


class SourceRecord(BaseModel):
    """One official source listed in the ingestion registry."""

    source_id: str
    category: str
    document_type: str
    url: AnyUrl
    source_format: SourceFormat
    collection: KnowledgeCollection
    authority: str = "ADGM"
    jurisdiction: str = "ADGM"
    official_source: bool = True
    notes: str | None = None


class SourceManifest(BaseModel):
    """Versioned source registry extracted from Data Sources.docx."""

    generated_at: datetime
    source_document: str
    sources: list[SourceRecord]


class NormalizedSection(BaseModel):
    """A structure-preserving section extracted from a source document."""

    heading: str | None = None
    section_path: list[str] = Field(default_factory=list)
    text: str
    page_number: int | None = None
    tables: list[list[list[str]]] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    """Common intermediate format used before chunking."""

    source: SourceRecord
    title: str
    downloaded_path: str | None = None
    file_hash: str | None = None
    extracted_at: datetime
    sections: list[NormalizedSection]


class KnowledgeChunk(BaseModel):
    """A retrieval-ready chunk with citation-grade metadata."""

    chunk_id: str
    source_id: str
    collection: KnowledgeCollection
    text: str
    metadata: dict[str, Any]

