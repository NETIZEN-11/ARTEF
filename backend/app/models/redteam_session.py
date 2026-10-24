from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import UUIDString
from app.models.user import Base


class RedTeamSessionRecord(Base):
    """A finished multi-turn red-team session: strategy, full transcript and verdict."""

    __tablename__ = "redteam_sessions"

    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    target_agent_id: Mapped[str | None] = mapped_column(
        UUIDString(), ForeignKey("target_agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # [{turn_number, prompt, response, tool_calls, judge_verdict, judge_rationale}]
    turns: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    final_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    objective_achieved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        UUIDString(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_redteam_sessions_created_at", "created_at"),)
