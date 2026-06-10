"""Violation API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.violation import Violation
from backend.app.schemas.violation import ViolationCreate, ViolationRead, ViolationUpdate

router = build_crud_router(
    model=Violation,
    create_schema=ViolationCreate,
    update_schema=ViolationUpdate,
    read_schema=ViolationRead,
    prefix="/violations",
    tags=["violations"],
)

