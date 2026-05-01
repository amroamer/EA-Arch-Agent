"""SQLAlchemy ORM models — currently just the `sessions` table.

A `Session` is a single Analyze or Compare invocation. We persist the
prompt, the resulting Markdown response, and metadata so the frontend
History sidebar can list and reload past results.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Session(Base):
    """One Analyze or Compare invocation."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    # 'analyze' or 'compare'
    session_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # AnalysisMode value, only set for analyze
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Persona value, only when mode == 'persona'
    persona: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # JSON list[str] of focus areas, only when mode == 'detailed'
    focus_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hashes (sha256 hex) of the input images. Used as content-addressable
    # keys; doesn't store actual image bytes (could later store in S3/blob).
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_image_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    response_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compliance-mode result: list of per-framework scorecards.
    # Shape: [{framework_id, framework_name, narrative_markdown, weighted_score,
    #          items: [{framework_item_id, criteria, weight_planned,
    #                   compliance_pct, remarks}]}]
    # Only populated when mode == 'compliance'.
    scorecards: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    # 'running' | 'done' | 'error'
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Performance metrics (set when session moves to 'done')
    ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def prompt_preview(self) -> str | None:
        """First ~80 chars of user_prompt, for the history sidebar."""
        if not self.user_prompt:
            return None
        return self.user_prompt[:80] + ("…" if len(self.user_prompt) > 80 else "")


class Framework(Base):
    """An EA compliance framework — e.g., 'AWS Well-Architected', 'TOGAF', 'Zero Trust'.

    Has many FrameworkItems (the criteria / scorecard rows).
    """

    __tablename__ = "frameworks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    items: Mapped[list["FrameworkItem"]] = relationship(
        back_populates="framework",
        cascade="all, delete-orphan",
        order_by="FrameworkItem.sort_order",
    )


class FrameworkItem(Base):
    """One row in a Framework's compliance scorecard."""

    __tablename__ = "framework_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    framework_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    criteria: Mapped[str] = mapped_column(Text, nullable=False)
    # Planned weight (0-100): the criterion's importance within the
    # framework. Per-analysis values (actual weight, compliance %, remarks)
    # are NOT stored here — they live on Session.scorecards (JSON) so each
    # analysis instance has its own scorecard without mutating the template.
    weight_planned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped["Framework"] = relationship(back_populates="items")


class Image(Base):
    """Content-addressable image storage.

    Keyed by sha256 of the original (pre-resize) bytes; multiple Sessions
    that reference the same image only store the bytes once. Stores the
    *resized* bytes (≤1568 px longest edge) — the originals are discarded.
    """

    __tablename__ = "images"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
