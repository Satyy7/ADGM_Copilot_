"""Generated clause API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.generated_clause import GeneratedClause
from backend.app.schemas.generated_clause import (
    GeneratedClauseCreate,
    GeneratedClauseRead,
    GeneratedClauseUpdate,
)

router = build_crud_router(
    model=GeneratedClause,
    create_schema=GeneratedClauseCreate,
    update_schema=GeneratedClauseUpdate,
    read_schema=GeneratedClauseRead,
    prefix="/generated-clauses",
    tags=["generated clauses"],
)

