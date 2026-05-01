"""FastAPI application entrypoint.

The app is mounted under `BASE_PATH` (default `/arch-assistant`) so that
nginx can route the entire path prefix to this service in production. In
development, the Vite dev server proxies the API path to the backend
directly.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import configure_logging
from app.routes import (
    analyze,
    compare,
    frameworks,
    health,
    images,
    mock_stream,
    prompts,
    sessions,
)

# ── Logging configuration ──────────────────────────────────────────────
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run init_db on startup so the app works on first run without
    requiring `alembic upgrade head`. In prod, prefer Alembic migrations."""
    logger.info("Initializing database tables...")
    try:
        await init_db()
        logger.info("Database ready")
    except Exception:
        # Don't crash the app — DB may come up shortly. /health will
        # surface the issue.
        logger.exception("init_db failed; continuing without tables")
    yield


app = FastAPI(
    title="EA Arch Agent",
    version="1.0.0",
    docs_url=f"{settings.base_path}/api/docs",
    openapi_url=f"{settings.base_path}/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────
# Exact-origin allow-list (no wildcards) since SSE consumers may use
# `credentials: 'include'`.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Accel-Buffering"],
)

# ── Routers ────────────────────────────────────────────────────────────
api_prefix = f"{settings.base_path}/api"

app.include_router(health.router, prefix=api_prefix, tags=["health"])
app.include_router(analyze.router, prefix=api_prefix, tags=["analyze"])
app.include_router(compare.router, prefix=api_prefix, tags=["compare"])
app.include_router(sessions.router, prefix=api_prefix, tags=["sessions"])
app.include_router(images.router, prefix=api_prefix, tags=["images"])
app.include_router(frameworks.router, prefix=api_prefix, tags=["frameworks"])
app.include_router(prompts.router, prefix=api_prefix, tags=["prompts"])
app.include_router(mock_stream.router, prefix=api_prefix, tags=["dev"])


@app.get("/")
async def root_redirect():
    """Health-friendly root response — sometimes useful for load balancers."""
    return {"app": "ea-arch-agent", "base_path": settings.base_path}
