"""GET /health — readiness probe for Ollama + DB."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine, get_db
from app.models.responses import HealthResponse
from app.ollama_client import check_health as ollama_check
from app.services.llm_config import fetch_active_llm_config

router = APIRouter()

_started_at = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    # Resolve the user's saved model (Settings → LLM Model). Falls back to
    # the env default when no row exists. We probe Ollama for *that* model
    # so /health reflects what analyses will actually use.
    try:
        active = await fetch_active_llm_config(db)
        target_model = active.model
    except Exception:  # noqa: BLE001 — DB issues surface as `down` below
        target_model = settings.ollama_model

    reachable, model_present, ollama_err = await ollama_check(target_model)

    db_ok = True
    db_err: str | None = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — surface any error in /health
        db_ok = False
        db_err = str(exc)

    if reachable and model_present and db_ok:
        status = "ok"
        err = None
    elif reachable and db_ok:
        status = "degraded"
        err = f"model {target_model} not loaded"
    else:
        status = "down"
        err = "; ".join(filter(None, [ollama_err, db_err]))

    return HealthResponse(
        status=status,
        ollama_reachable=reachable,
        model_loaded=model_present,
        model_name=target_model,
        uptime_seconds=time.monotonic() - _started_at,
        error=err,
    )
