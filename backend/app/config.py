"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate types and provide defaults. Settings are
loaded once via the `settings` singleton at module import time.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Ollama ─────────────────────────────────────────────────────────
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5vl:7b"
    # int because pydantic accepts -1 / "-1"; -1 means pin in VRAM forever.
    ollama_keep_alive: int = -1

    # ── Database ───────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://kpmg:kpmg@db:5432/kpmg_arch"
    )

    # ── App routing ────────────────────────────────────────────────────
    base_path: str = "/arch-assistant"

    # CORS allow-list. Comma-separated in env, parsed to list at runtime.
    cors_origins: str = "http://localhost:5173,http://localhost"

    # ── Upload limits ──────────────────────────────────────────────────
    max_upload_bytes: int = 15_728_640  # 15 MB
    image_resize_max_edge: int = 1568   # px (Gemma vision tile preference)

    # ── Logging ────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
