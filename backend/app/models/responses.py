"""Pydantic response models for non-streaming endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str  # ok | degraded | down
    ollama_reachable: bool
    model_loaded: bool
    model_name: str
    uptime_seconds: float
    error: str | None = None


class SessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_type: str
    mode: str | None
    persona: str | None
    prompt_preview: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None
    total_ms: int | None


class SessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_type: str
    mode: str | None
    persona: str | None
    focus_areas: list[str] | None
    user_prompt: str | None
    image_hash: str | None
    reference_image_hash: str | None
    response_markdown: str | None
    scorecards: list[dict] | None = None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    ttft_ms: int | None
    total_ms: int | None
