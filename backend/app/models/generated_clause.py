"""Generated clause model.

Clause generation results are stored for reuse, auditability, and later
similar-template retrieval.
"""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class GeneratedClause(TimestampMixin, Base):
    """A clause generated from regulations and template context."""

    __tablename__ = "generated_clauses"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    request_text: Mapped[str] = mapped_column(Text)
    clause_type: Mapped[str | None] = mapped_column(String(150), index=True)
    generated_text: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(150))
    retrieval_payload: Mapped[dict | None] = mapped_column(JSONB)
    citation_payload: Mapped[dict | None] = mapped_column(JSONB)
    validation_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
    )

    user = relationship("User", back_populates="generated_clauses")

