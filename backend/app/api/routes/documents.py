"""Document metadata API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate

router = build_crud_router(
    model=Document,
    create_schema=DocumentCreate,
    update_schema=DocumentUpdate,
    read_schema=DocumentRead,
    prefix="/documents",
    tags=["documents"],
)

