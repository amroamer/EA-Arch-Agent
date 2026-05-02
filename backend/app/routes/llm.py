"""LLM model & sampling-parameter management (Settings → LLM Model).

Endpoints:
  GET  /llm/models   — proxy /api/tags from the configured Ollama daemon
  GET  /llm/config   — current saved config (or settings-derived defaults)
  PUT  /llm/config   — upsert the singleton `llm_config` row
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.db import LLMConfig
from app.services.llm_config import DEFAULT_KEY, fetch_active_llm_config

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────


class ModelInfo(BaseModel):
    """One row of /api/tags from Ollama."""

    name: str
    size_bytes: int
    modified_at: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    family: str | None = None


class LLMConfigBody(BaseModel):
    model: str = Field(..., min_length=1, max_length=200)
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    num_ctx: int = Field(16_384, ge=512, le=131_072)
    num_predict: int = Field(4096, ge=-1, le=131_072)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    top_k: int | None = Field(None, ge=1, le=10_000)
    repeat_penalty: float | None = Field(None, ge=0.5, le=2.0)
    seed: int | None = None
    keep_alive: str = Field("-1", min_length=1, max_length=32)


class LLMConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model: str
    temperature: float
    num_ctx: int
    num_predict: int
    top_p: float | None
    top_k: int | None
    repeat_penalty: float | None
    seed: int | None
    keep_alive: str
    is_overridden: bool   # True if a row exists; False = falling back to defaults
    updated_at: datetime | None


# ── /llm/models — proxy Ollama's catalogue ─────────────────────────────


@router.get("/llm/models", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """Return the model catalogue of the configured Ollama daemon."""
    url = f"{settings.ollama_host.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            502,
            f"Could not reach Ollama at {settings.ollama_host}: {exc}",
        )

    out: list[ModelInfo] = []
    for m in payload.get("models", []):
        details = m.get("details") or {}
        out.append(
            ModelInfo(
                name=m.get("name") or m.get("model") or "?",
                size_bytes=int(m.get("size") or 0),
                modified_at=m.get("modified_at"),
                parameter_size=details.get("parameter_size"),
                quantization=details.get("quantization_level"),
                family=details.get("family"),
            )
        )
    # Sort by name for stable UI listing.
    out.sort(key=lambda x: x.name.lower())
    return out


# ── /llm/config — get & upsert the saved config ────────────────────────


@router.get("/llm/config", response_model=LLMConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)) -> LLMConfigResponse:
    """Return the active config — DB row if present, defaults otherwise."""
    row = await db.get(LLMConfig, DEFAULT_KEY)
    if row is not None:
        return LLMConfigResponse(
            model=row.model,
            temperature=row.temperature,
            num_ctx=row.num_ctx,
            num_predict=row.num_predict,
            top_p=row.top_p,
            top_k=row.top_k,
            repeat_penalty=row.repeat_penalty,
            seed=row.seed,
            keep_alive=row.keep_alive,
            is_overridden=True,
            updated_at=row.updated_at,
        )
    # Defaults (mirrors fetch_active_llm_config's fallback path).
    active = await fetch_active_llm_config(db)
    return LLMConfigResponse(
        model=active.model,
        temperature=active.temperature,
        num_ctx=active.num_ctx,
        num_predict=active.num_predict,
        top_p=active.top_p,
        top_k=active.top_k,
        repeat_penalty=active.repeat_penalty,
        seed=active.seed,
        keep_alive=active.keep_alive,
        is_overridden=False,
        updated_at=None,
    )


@router.put("/llm/config", response_model=LLMConfigResponse)
async def upsert_config(
    body: LLMConfigBody,
    db: AsyncSession = Depends(get_db),
) -> LLMConfigResponse:
    """Save (or replace) the singleton config row."""
    existing = await db.get(LLMConfig, DEFAULT_KEY)
    if existing is None:
        existing = LLMConfig(id=DEFAULT_KEY, model=body.model)
        db.add(existing)

    existing.model = body.model
    existing.temperature = body.temperature
    existing.num_ctx = body.num_ctx
    existing.num_predict = body.num_predict
    existing.top_p = body.top_p
    existing.top_k = body.top_k
    existing.repeat_penalty = body.repeat_penalty
    existing.seed = body.seed
    existing.keep_alive = body.keep_alive

    await db.commit()
    await db.refresh(existing)

    logger.info(
        "llm_config_saved",
        extra={
            "model": existing.model,
            "temperature": existing.temperature,
            "num_ctx": existing.num_ctx,
            "num_predict": existing.num_predict,
        },
    )
    return LLMConfigResponse(
        model=existing.model,
        temperature=existing.temperature,
        num_ctx=existing.num_ctx,
        num_predict=existing.num_predict,
        top_p=existing.top_p,
        top_k=existing.top_k,
        repeat_penalty=existing.repeat_penalty,
        seed=existing.seed,
        keep_alive=existing.keep_alive,
        is_overridden=True,
        updated_at=existing.updated_at,
    )
