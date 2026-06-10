"""Compliance review API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.review import Review
from backend.app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate

router = build_crud_router(
    model=Review,
    create_schema=ReviewCreate,
    update_schema=ReviewUpdate,
    read_schema=ReviewRead,
    prefix="/reviews",
    tags=["reviews"],
)

