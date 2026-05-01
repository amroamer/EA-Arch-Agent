"""GET /health — readiness probe for Ollama + DB."""
from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.models.responses import HealthResponse
from app.ollama_client import check_health as ollama_check

router = APIRouter()

_started_at = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    reachable, model_present, ollama_err = await ollama_check()

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
        err = f"model {settings.ollama_model} not loaded"
    else:
        status = "down"
        err = "; ".join(filter(None, [ollama_err, db_err]))

    return HealthResponse(
        status=status,
        ollama_reachable=reachable,
        model_loaded=model_present,
        model_name=settings.ollama_model,
        uptime_seconds=time.monotonic() - _started_at,
        error=err,
    )
