"""User persistence API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserRead, UserUpdate

router = build_crud_router(
    model=User,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    read_schema=UserRead,
    prefix="/users",
    tags=["users"],
)

