"""User model.

Users own uploaded documents, reviews, generated clauses, audit logs, and query
logs. Authentication can be added later without changing these relationships.
"""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    """Application user or compliance operator."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents = relationship("Document", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    generated_clauses = relationship("GeneratedClause", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    query_logs = relationship("QueryLog", back_populates="user")

