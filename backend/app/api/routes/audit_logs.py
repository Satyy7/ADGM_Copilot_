"""Audit log API routes."""

from backend.app.api.routes.crud import build_crud_router
from backend.app.models.audit_log import AuditLog
from backend.app.schemas.audit_log import AuditLogCreate, AuditLogRead

router = build_crud_router(
    model=AuditLog,
    create_schema=AuditLogCreate,
    update_schema=None,
    read_schema=AuditLogRead,
    prefix="/audit-logs",
    tags=["audit logs"],
)

