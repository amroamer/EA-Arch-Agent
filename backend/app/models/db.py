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

    # Rationale fields surfaced to the model in the per-criterion prompt
    # (see compliance_per_criterion_v2 in app/prompts/defaults.py). Both
    # nullable: criteria created via the Settings UI before this column
    # existed — or new ones the consultant hasn't filled in yet — render
    # cleanly because the prompt builder skips empty lines.
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_pass_looks_like: Mapped[str | None] = mapped_column(Text, nullable=True)

    framework: Mapped["Framework"] = relationship(back_populates="items")


class LLMConfig(Base):
    """Singleton row holding the user's chosen LLM model + sampling params.

    When this row exists, every Ollama call (analyze / compare / compliance)
    pulls the model name and generation knobs from here instead of the
    OLLAMA_MODEL env var or hard-coded defaults. Editable via Settings →
    LLM Model.

    `id` is fixed to the literal "default" so we always have at most one
    row — easier than a singleton constraint.
    """

    __tablename__ = "llm_config"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="default")

    # Model tag, e.g. "qwen2.5vl:7b" or "gemma4:latest". Must match a
    # model present on the configured Ollama daemon (see /llm/models).
    model: Mapped[str] = mapped_column(String(200), nullable=False)

    # Generation knobs — passed straight through to Ollama's `options`.
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    num_ctx: Mapped[int] = mapped_column(Integer, nullable=False, default=16_384)
    num_predict: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)

    # Optional sampling knobs — null means "let Ollama use its default".
    top_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Ollama keep_alive: "-1" pins forever, "30m" unloads after idle, "0"
    # unloads immediately. Stored as string to match Ollama's accepted forms.
    keep_alive: Mapped[str] = mapped_column(String(32), nullable=False, default="-1")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


class PromptOverride(Base):
    """User-saved override for one of the built-in prompt templates.

    Defaults live in app/prompts/defaults.py (Python source). When a row
    exists here, its `template` is preferred over the default. "Reset to
    default" simply deletes the row.
    """

    __tablename__ = "prompt_overrides"

    # Stable key matching app.prompts.defaults.DEFAULTS — e.g.
    # 'analyze_quick', 'analyze_compliance'. Acts as primary key.
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )


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
