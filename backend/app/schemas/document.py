"""Document API schemas."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import (
    IdentifierSchema,
    JsonDict,
    SchemaBase,
    TimestampSchema,
)


class DocumentCreate(SchemaBase):
    """Metadata captured when a document is uploaded."""

    user_id: UUID | None = None
    original_filename: str = Field(..., max_length=500)
    storage_path: str | None = None
    mime_type: str | None = Field(default=None, max_length=150)
    file_extension: str = Field(..., max_length=20)
    file_size_bytes: int | None = Field(default=None, ge=0)
    sha256_hash: str | None = Field(default=None, min_length=64, max_length=64)
    detected_document_type: str | None = Field(default=None, max_length=150)
    extraction_status: str = Field(default="pending", max_length=50)
    extracted_text: str | None = None
    doc_metadata: JsonDict | None = None


class DocumentUpdate(SchemaBase):
    """Mutable document metadata and extraction fields."""

    storage_path: str | None = None
    mime_type: str | None = Field(default=None, max_length=150)
    file_size_bytes: int | None = Field(default=None, ge=0)
    sha256_hash: str | None = Field(default=None, min_length=64, max_length=64)
    detected_document_type: str | None = Field(default=None, max_length=150)
    extraction_status: str | None = Field(default=None, max_length=50)
    extracted_text: str | None = None
    doc_metadata: JsonDict | None = None


class DocumentRead(IdentifierSchema, TimestampSchema):
    """Document response schema."""

    user_id: UUID | None
    original_filename: str
    storage_path: str | None
    mime_type: str | None
    file_extension: str
    file_size_bytes: int | None
    sha256_hash: str | None
    detected_document_type: str | None
    extraction_status: str
    extracted_text: str | None
    doc_metadata: JsonDict | None

