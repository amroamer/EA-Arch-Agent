"""Async helper to resolve the current template for a prompt key.

Order:
  1. Check `prompt_overrides` table for a row keyed by `key`. If found,
     return that template (the user has customised it via Settings).
  2. Otherwise fall back to the built-in default in
     app.prompts.defaults.DEFAULTS.

Use from the analyze / compare routes to fetch the template just before
building the prompt for a request. Importing this module is cheap; the
DB hit only happens when fetch_template() is called.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import PromptOverride
from app.prompts.defaults import DEFAULTS


async def fetch_template(db: AsyncSession, key: str) -> str:
    """Return the active template for `key` — override if set, else default."""
    if key not in DEFAULTS:
        raise KeyError(f"unknown prompt key: {key!r}")
    row = await db.get(PromptOverride, key)
    return row.template if row is not None else DEFAULTS[key]["template"]
