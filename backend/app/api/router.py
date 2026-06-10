"""Top-level API router registration."""

from fastapi import APIRouter

from backend.app.api.routes import (
    audit_logs,
    chat,
    documents,
    generated_clauses,
    query_logs,
    recommendations,
    reviews,
    users,
    violations,
)

api_router = APIRouter(prefix="/api/v1")

# RAG endpoints
api_router.include_router(chat.router)

# Persistence endpoints
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(reviews.router)
api_router.include_router(violations.router)
api_router.include_router(recommendations.router)
api_router.include_router(generated_clauses.router)
api_router.include_router(audit_logs.router)
api_router.include_router(query_logs.router)

