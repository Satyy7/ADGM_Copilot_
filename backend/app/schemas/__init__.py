"""Pydantic schemas for API request and response contracts."""

from backend.app.schemas.audit_log import AuditLogCreate, AuditLogRead
from backend.app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from backend.app.schemas.generated_clause import (
    GeneratedClauseCreate,
    GeneratedClauseRead,
    GeneratedClauseUpdate,
)
from backend.app.schemas.query_log import QueryLogCreate, QueryLogRead, QueryLogUpdate
from backend.app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationRead,
    RecommendationUpdate,
)
from backend.app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate
from backend.app.schemas.source import (
    KnowledgeChunk,
    NormalizedDocument,
    NormalizedSection,
    SourceManifest,
    SourceRecord,
)
from backend.app.schemas.user import UserCreate, UserRead, UserUpdate
from backend.app.schemas.rag import ChatRequest, CitationSource, RAGResponse, RetrievedChunk
from backend.app.schemas.violation import ViolationCreate, ViolationRead, ViolationUpdate

__all__ = [
    "AuditLogCreate",
    "AuditLogRead",
    "DocumentCreate",
    "DocumentRead",
    "DocumentUpdate",
    "GeneratedClauseCreate",
    "GeneratedClauseRead",
    "GeneratedClauseUpdate",
    "QueryLogCreate",
    "QueryLogRead",
    "QueryLogUpdate",
    "RecommendationCreate",
    "RecommendationRead",
    "RecommendationUpdate",
    "ReviewCreate",
    "ReviewRead",
    "ReviewUpdate",
    "ChatRequest",
    "CitationSource",
    "RAGResponse",
    "RetrievedChunk",
    "KnowledgeChunk",
    "NormalizedDocument",
    "NormalizedSection",
    "SourceManifest",
    "SourceRecord",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "ViolationCreate",
    "ViolationRead",
    "ViolationUpdate",
]
