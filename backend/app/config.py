"""Application configuration loaded from environment variables.

Uses pydantic-settings. Resolution order (highest priority wins):

    1. Process environment variables — what the kpmg-infra orchestrator
       injects in production (DATABASE_URL, OLLAMA_HOST come in this way).
    2. `.env.local` — gitignored, for personal local overrides.
    3. `.env` — committed defaults checked into the repo. Required to
       exist so the prod deploy's `env_file:` directive doesn't fail.

Every field has a default so the app boots even with a totally missing
.env file. The startup validator (`validate_critical_settings()`) is
called from main.py's lifespan and surfaces deployment misconfigurations
clearly — fails fast on placeholder values for vars the orchestrator is
expected to inject, warns on non-critical placeholders.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# Sentinel string used in the committed .env for values that MUST be
# supplied by the deployment (either via orchestrator-injected env or
# via .env.local for local dev). The startup validator looks for this
# token to surface misconfigurations.
PLACEHOLDER_TOKEN = "CHANGE_ME_IN_PRODUCTION"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Files load in order; later files win on conflict. Process env
        # always wins over both. .env.local is optional — pydantic-settings
        # silently skips files that don't exist when listed this way.
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Ollama ─────────────────────────────────────────────────────────
    # OLLAMA_HOST: injected by kpmg-infra in prod. Default works for the
    # local docker-compose setup (where the ollama service is reachable
    # under the DNS name `ollama`).
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5vl:7b"
    # int because pydantic accepts -1 / "-1"; -1 means pin in VRAM forever.
    ollama_keep_alive: int = -1

    # ── Database ───────────────────────────────────────────────────────
    # DATABASE_URL: injected by kpmg-infra in prod. Default works for the
    # local docker-compose setup.
    database_url: str = "postgresql+asyncpg://kpmg:kpmg@db:5432/kpmg_arch"

    # ── App routing ────────────────────────────────────────────────────
    base_path: str = "/EAArchAgent"

    # CORS allow-list. Comma-separated in env, parsed to list at runtime.
    cors_origins: str = "http://localhost:5173,http://localhost"

    # ── Upload limits ──────────────────────────────────────────────────
    max_upload_bytes: int = 15_728_640  # 15 MB
    image_resize_max_edge: int = 1568   # px (vision tile preference)

    # ── Logging ────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# ── Startup validator ─────────────────────────────────────────────────


class CriticalConfigError(RuntimeError):
    """Raised at startup when a critical env var is missing / placeholder."""


def _looks_like_placeholder(value: str) -> bool:
    """True if `value` is empty, the sentinel token, or all-uppercase
    'CHANGE_ME...' / 'REPLACE_ME...' style. Case-insensitive prefix match
    so 'change_me_in_production' or 'CHANGE_ME' both trip."""
    if not value:
        return True
    v = value.strip().lower()
    if not v:
        return True
    return v.startswith("change_me") or v.startswith("replace_me") or v == "todo"


def _sanitize_for_log(name: str, value: str) -> str:
    """Mask credentials so we don't print Postgres passwords to logs."""
    if name == "database_url" and "://" in value:
        try:
            scheme, rest = value.split("://", 1)
            if "@" in rest:
                _creds, host = rest.rsplit("@", 1)
                return f"{scheme}://***@{host}"
        except Exception:  # noqa: BLE001
            pass
    return value


def validate_critical_settings(s: Settings | None = None) -> None:
    """Called from the FastAPI lifespan on startup.

    - Logs every loaded setting with sanitized credentials.
    - Fails fast (raises CriticalConfigError) when a CRITICAL var is
      empty or a placeholder. Critical = the orchestrator MUST inject it
      in prod, and missing it means the app cannot function meaningfully.
    - Logs WARNING for non-critical placeholders so operators see them
      in startup logs without crashing the container.
    """
    s = s or settings

    fields = {
        "ollama_host": s.ollama_host,
        "ollama_model": s.ollama_model,
        "ollama_keep_alive": str(s.ollama_keep_alive),
        "database_url": s.database_url,
        "base_path": s.base_path,
        "cors_origins": s.cors_origins,
        "max_upload_bytes": str(s.max_upload_bytes),
        "image_resize_max_edge": str(s.image_resize_max_edge),
        "log_level": s.log_level,
    }
    for name, raw in fields.items():
        logger.info("config: %s=%s", name, _sanitize_for_log(name, raw))

    # Critical: app cannot do its job without these. Prod orchestrator
    # injects them; a placeholder here means the deploy is misconfigured.
    critical = {
        "OLLAMA_HOST": s.ollama_host,
        "DATABASE_URL": s.database_url,
    }
    for name, value in critical.items():
        if _looks_like_placeholder(value):
            raise CriticalConfigError(
                f"{name} is unset or a placeholder ({value!r}). "
                f"In production this is injected by kpmg-infra; check the "
                f"orchestrator's env injection. For local dev, set it in "
                f".env.local."
            )

    # Non-critical: surface placeholders so they're visible but allow
    # boot — the app still functions, possibly with reduced features
    # (e.g. CORS too strict, log level wrong, model name not pulled).
    optional_with_placeholder_check = {
        "OLLAMA_MODEL": s.ollama_model,
        "BASE_PATH": s.base_path,
        "CORS_ORIGINS": s.cors_origins,
        "LOG_LEVEL": s.log_level,
    }
    for name, value in optional_with_placeholder_check.items():
        if _looks_like_placeholder(value):
            logger.warning(
                "config: %s is a placeholder (%r); using default behaviour. "
                "Set it in .env or .env.local for proper behaviour.",
                name,
                value,
            )
