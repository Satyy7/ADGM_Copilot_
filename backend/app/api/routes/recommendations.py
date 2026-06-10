"""Recommendation API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.recommendation import Recommendation
from backend.app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationRead,
    RecommendationUpdate,
)

router = build_crud_router(
    model=Recommendation,
    create_schema=RecommendationCreate,
    update_schema=RecommendationUpdate,
    read_schema=RecommendationRead,
    prefix="/recommendations",
    tags=["recommendations"],
)

