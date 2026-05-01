"""Pydantic schemas for the EA compliance framework endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FrameworkItemBase(BaseModel):
    """Editable fields of a framework item."""

    criteria: str = Field(..., min_length=1, max_length=4000)
    weight_planned: float = Field(0.0, ge=0, le=100)
    sort_order: int = 0


class FrameworkItemRead(FrameworkItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class FrameworkBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)


class FrameworkUpsert(FrameworkBase):
    """Body for create / full-update — items list fully replaces existing."""

    items: list[FrameworkItemBase] = Field(default_factory=list)


class FrameworkSummary(FrameworkBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
    item_count: int


class FrameworkDetail(FrameworkBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
    items: list[FrameworkItemRead]
