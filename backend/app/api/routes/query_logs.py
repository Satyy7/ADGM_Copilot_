"""Query log API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.query_log import QueryLog
from backend.app.schemas.query_log import QueryLogCreate, QueryLogRead, QueryLogUpdate

router = build_crud_router(
    model=QueryLog,
    create_schema=QueryLogCreate,
    update_schema=QueryLogUpdate,
    read_schema=QueryLogRead,
    prefix="/query-logs",
    tags=["query logs"],
)

