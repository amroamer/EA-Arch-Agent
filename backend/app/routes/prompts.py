"""CRUD for prompt overrides (Settings → Prompts page).

Each prompt is identified by a stable `key` — see app.prompts.defaults.
The catalogue (name, description, list of required placeholders) lives
in code; the user can save a customised `template` per key in the
`prompt_overrides` table. Resetting deletes the override, restoring the
default.

Endpoints:
  GET    /prompts             — list every key with default + current template
  GET    /prompts/{key}       — single (same shape as a list element)
  PUT    /prompts/{key}       — upsert override; validates required placeholders
  DELETE /prompts/{key}       — reset to default (deletes override row)
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import PromptOverride
from app.prompts.defaults import DEFAULTS

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────


class PromptItem(BaseModel):
    """One prompt's full state — default + current (override or default)."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    description: str
    placeholders: list[str]
    default_template: str
    current_template: str
    is_overridden: bool
    updated_at: str | None = None  # ISO timestamp, only when overridden


class PromptUpdate(BaseModel):
    template: str = Field(..., min_length=1, max_length=64_000)


# ── Helpers ────────────────────────────────────────────────────────────


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _placeholders_in(template: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(template))


def _validate_template(key: str, template: str) -> None:
    """Required placeholders for the key MUST appear in the template,
    else .format(...) at request time will raise KeyError and the
    analysis will fail. We enforce this on save."""
    if key not in DEFAULTS:
        raise HTTPException(404, f"Unknown prompt key: {key!r}")
    required = set(DEFAULTS[key]["placeholders"])
    present = _placeholders_in(template)
    missing = required - present
    if missing:
        raise HTTPException(
            400,
            f"Template is missing required placeholders: {sorted(missing)}. "
            f"Each must appear as {{name}} somewhere in the template.",
        )


def _row_to_item(key: str, override: PromptOverride | None) -> PromptItem:
    spec = DEFAULTS[key]
    if override is not None:
        return PromptItem(
            key=key,
            name=spec["name"],
            description=spec["description"],
            placeholders=list(spec["placeholders"]),
            default_template=spec["template"],
            current_template=override.template,
            is_overridden=True,
            updated_at=override.updated_at.isoformat(),
        )
    return PromptItem(
        key=key,
        name=spec["name"],
        description=spec["description"],
        placeholders=list(spec["placeholders"]),
        default_template=spec["template"],
        current_template=spec["template"],
        is_overridden=False,
        updated_at=None,
    )


# ── Routes ─────────────────────────────────────────────────────────────


@router.get("/prompts", response_model=list[PromptItem])
async def list_prompts(db: AsyncSession = Depends(get_db)) -> list[PromptItem]:
    """All known prompts, override status hydrated."""
    rows = (await db.execute(select(PromptOverride))).scalars().all()
    by_key = {r.key: r for r in rows}
    return [_row_to_item(k, by_key.get(k)) for k in DEFAULTS]


@router.get("/prompts/{key}", response_model=PromptItem)
async def get_prompt(key: str, db: AsyncSession = Depends(get_db)) -> PromptItem:
    if key not in DEFAULTS:
        raise HTTPException(404, f"Unknown prompt key: {key!r}")
    override = await db.get(PromptOverride, key)
    return _row_to_item(key, override)


@router.put("/prompts/{key}", response_model=PromptItem)
async def upsert_prompt(
    key: str,
    body: PromptUpdate,
    db: AsyncSession = Depends(get_db),
) -> PromptItem:
    """Upsert an override. Validates required placeholders are still present."""
    _validate_template(key, body.template)

    existing = await db.get(PromptOverride, key)
    if existing is None:
        existing = PromptOverride(key=key, template=body.template)
        db.add(existing)
    else:
        existing.template = body.template

    await db.commit()
    await db.refresh(existing)

    logger.info(
        "prompt_override_saved",
        extra={"key": key, "template_chars": len(body.template)},
    )
    return _row_to_item(key, existing)


@router.delete("/prompts/{key}")
async def reset_prompt(key: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Reset to default — deletes the override row if any."""
    if key not in DEFAULTS:
        raise HTTPException(404, f"Unknown prompt key: {key!r}")
    existing = await db.get(PromptOverride, key)
    if existing is not None:
        await db.delete(existing)
        await db.commit()
        logger.info("prompt_override_reset", extra={"key": key})
    return Response(status_code=204)
