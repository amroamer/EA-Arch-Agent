"""FastAPI application entrypoint.

Routing model:
    Browser  → https://host/EAArchAgent/api/sessions
    nginx    → strips /EAArchAgent, forwards /api/sessions to backend
    Backend  → mounts routes at /api/sessions (no public-prefix awareness
               in the URL itself)

We tell FastAPI about the public prefix via `root_path=settings.base_path`
so the OpenAPI spec and Swagger UI emit browser-correct URLs (i.e. they
include /EAArchAgent in their links) even though every route is mounted
at /api internally. The Vite dev proxy mirrors the nginx rewrite — see
frontend/vite.config.ts — so dev and prod behave identically.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_critical_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.routes import (
    analyze,
    compare,
    frameworks,
    health,
    images,
    llm,
    mock_stream,
    prompts,
    sessions,
)

# ── Logging configuration ──────────────────────────────────────────────
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks: env-var validation, then DB init.

    - validate_critical_settings raises if DATABASE_URL or OLLAMA_HOST are
      still placeholders (deploy misconfiguration). Non-critical missing
      vars log a warning but don't crash the container.
    - init_db is best-effort: a transient DB outage shouldn't crash the
      app — `/health` will surface the issue and the app will recover
      when the DB returns.
    """
    validate_critical_settings()  # raises on critical misconfig

    logger.info("Initializing database tables...")
    try:
        await init_db()
        logger.info("Database ready")
    except Exception:
        logger.exception("init_db failed; continuing without tables")
    yield


app = FastAPI(
    title="EA Arch Agent",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    # Public URL prefix (nginx + Vite proxy strip this before forwarding).
    # FastAPI uses root_path to render correct absolute URLs in the
    # OpenAPI spec, the Swagger UI, and `request.url_for()` calls.
    root_path=settings.base_path,
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
# Routes are mounted at /api/*, NOT /EAArchAgent/api/*. The /EAArchAgent
# prefix is a deployment-layer concern (nginx + the Vite dev proxy strip
# it before the request reaches the app). See module docstring.
api_prefix = "/api"

app.include_router(health.router, prefix=api_prefix, tags=["health"])
app.include_router(analyze.router, prefix=api_prefix, tags=["analyze"])
app.include_router(compare.router, prefix=api_prefix, tags=["compare"])
app.include_router(sessions.router, prefix=api_prefix, tags=["sessions"])
app.include_router(images.router, prefix=api_prefix, tags=["images"])
app.include_router(frameworks.router, prefix=api_prefix, tags=["frameworks"])
app.include_router(prompts.router, prefix=api_prefix, tags=["prompts"])
app.include_router(llm.router, prefix=api_prefix, tags=["llm"])
app.include_router(mock_stream.router, prefix=api_prefix, tags=["dev"])


@app.get("/")
async def root_redirect():
    """Health-friendly root response — sometimes useful for load balancers."""
    return {"app": "ea-arch-agent", "base_path": settings.base_path}
