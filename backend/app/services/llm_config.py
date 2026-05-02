"""Helper for resolving the active LLM configuration.

Order of precedence:
  1. The single `llm_config` row (set via Settings → LLM Model in the UI).
  2. Application defaults from `app.config.settings` (env-derived).

Returns a small dataclass-like dict the orchestrators can pass to
`stream_chat()` directly. None values for optional fields mean "use the
Ollama-side default".
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import LLMConfig

# Singleton row PK.
DEFAULT_KEY = "default"

# Hard-coded fallbacks used when no row in llm_config exists.
_FALLBACK_TEMPERATURE = 0.2
_FALLBACK_NUM_CTX = 16_384
_FALLBACK_NUM_PREDICT = 4096


@dataclass
class ActiveLLMConfig:
    model: str
    temperature: float
    num_ctx: int
    num_predict: int
    top_p: float | None
    top_k: int | None
    repeat_penalty: float | None
    seed: int | None
    keep_alive: str

    def as_options(self) -> dict[str, Any]:
        """Return the fields Ollama puts in its `options` map.
        None values are dropped so we don't shadow Ollama-side defaults."""
        out: dict[str, Any] = {
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }
        if self.top_p is not None:
            out["top_p"] = self.top_p
        if self.top_k is not None:
            out["top_k"] = self.top_k
        if self.repeat_penalty is not None:
            out["repeat_penalty"] = self.repeat_penalty
        if self.seed is not None:
            out["seed"] = self.seed
        return out

    def to_chat_kwargs(self) -> dict[str, Any]:
        """Spread directly into `stream_chat()`. Field names match the
        client's keyword arguments 1:1, so this is just `asdict()` with the
        intent made explicit."""
        return {
            "model": self.model,
            "keep_alive": self.keep_alive,
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "seed": self.seed,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def fetch_active_llm_config(db: AsyncSession) -> ActiveLLMConfig:
    """Return the active config: DB row if present, otherwise fallback to
    settings defaults. Always returns a complete ActiveLLMConfig."""
    row = await db.get(LLMConfig, DEFAULT_KEY)
    if row is not None:
        return ActiveLLMConfig(
            model=row.model,
            temperature=float(row.temperature),
            num_ctx=int(row.num_ctx),
            num_predict=int(row.num_predict),
            top_p=row.top_p,
            top_k=row.top_k,
            repeat_penalty=row.repeat_penalty,
            seed=row.seed,
            keep_alive=row.keep_alive,
        )
    # Fallback to env-derived settings.
    return ActiveLLMConfig(
        model=settings.ollama_model,
        temperature=_FALLBACK_TEMPERATURE,
        num_ctx=_FALLBACK_NUM_CTX,
        num_predict=_FALLBACK_NUM_PREDICT,
        top_p=None,
        top_k=None,
        repeat_penalty=None,
        seed=None,
        keep_alive=str(settings.ollama_keep_alive),
    )
