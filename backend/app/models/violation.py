"""Detected compliance violation model."""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class Violation(TimestampMixin, Base):
    """A specific compliance issue found during a review."""

    __tablename__ = "violations"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    review_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        index=True,
    )
    violation_type: Mapped[str] = mapped_column(String(150), index=True)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    regulation_reference: Mapped[str | None] = mapped_column(String(300), index=True)
    document_excerpt: Mapped[str | None] = mapped_column(Text)
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB)
    citation_payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)

    review = relationship("Review", back_populates="violations")
    recommendations = relationship("Recommendation", back_populates="violation")

