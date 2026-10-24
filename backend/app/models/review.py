from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ReviewLabel, ReviewStatus, SeverityLevel
from app.models.types import UUIDString
from app.models.user import Base


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    regression_id: Mapped[String] = mapped_column(
        UUIDString(),
        # RESTRICT: deleting a regression must not silently destroy the
        # review-queue entry and its labels.
        ForeignKey("regressions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[String] = mapped_column(
        UUIDString(), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, native_enum=False, create_constraint=True),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[String | None] = mapped_column(
        UUIDString(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    label: Mapped[ReviewLabel | None] = mapped_column(
        SQLEnum(ReviewLabel, native_enum=False, create_constraint=True),
        nullable=True,
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    regression: Mapped["Regression"] = relationship(back_populates="reviews", lazy="joined")
    run: Mapped["Run"] = relationship(back_populates="reviews", lazy="joined")
    assignee: Mapped[Optional["User"]] = relationship(lazy="joined")
    labels: Mapped[list["ReviewLabelRecord"]] = relationship(
        back_populates="review", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_review_queue_status_severity", "status", "severity"),
        Index("ix_review_queue_assigned", "assigned_to", "status"),
        UniqueConstraint("regression_id", name="uq_review_regression"),
    )


class ReviewLabelRecord(Base):
    __tablename__ = "review_labels"

    id: Mapped[String] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[String] = mapped_column(
        UUIDString(),
        ForeignKey("review_queue.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[ReviewLabel] = mapped_column(
        SQLEnum(ReviewLabel, native_enum=False, create_constraint=True),
        nullable=False,
    )
    # RESTRICT instead of CASCADE: deleting a user must not erase the
    # audit trail of which findings were labelled by whom.
    reviewer_id: Mapped[String] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review: Mapped["ReviewQueue"] = relationship(back_populates="labels", lazy="joined")
    reviewer: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (Index("ix_review_labels_review_created", "review_id", "created_at"),)
