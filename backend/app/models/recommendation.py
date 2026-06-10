"""Compliance recommendation model."""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class Recommendation(TimestampMixin, Base):
    """Recommended remediation for a review or a specific violation."""

    __tablename__ = "recommendations"

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
    violation_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("violations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300))
    recommendation_text: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50), default="medium", index=True)
    citation_payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)

    review = relationship("Review", back_populates="recommendations")
    violation = relationship("Violation", back_populates="recommendations")

