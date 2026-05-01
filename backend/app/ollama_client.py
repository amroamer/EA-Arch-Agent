"""Async streaming client for Ollama's /api/chat endpoint.

Tailored to the multimodal-streaming use case:
    - Sends images on the FIRST user message via the `images: []` field.
      Per Gemma 4 vision docs, image-before-text ordering matters.
    - Streams NDJSON via `aiter_bytes()` + manual line-buffering. (We do
      NOT use `aiter_lines()` — known CRLF edge-case in some httpx
      versions; manual buffering matches the proven pattern from
      Data-Steward-Assistant/server/ai-provider.ts:244-313.)
    - Wraps every call in a process-wide semaphore so concurrent requests
      serialize cleanly instead of fighting over a single VRAM-resident
      model. The second caller sees a `busy` event up-front.

Yields events of the form:
    {"type": "token",  "content": "..."}
    {"type": "done",   "total_ms": 12345, "ttft_ms": 234}
    {"type": "error",  "message": "...", "code": "..."}
    {"type": "busy",   "message": "Model in use, queued"}
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import settings
from app.utils.concurrency import ollama_semaphore

logger = logging.getLogger(__name__)

# 5 minute total timeout — typical /detailed request is 30-90s on a 5090.
_HTTP_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


class OllamaError(Exception):
    """Raised for non-200 responses or upstream connectivity problems."""


def _build_messages(
    *,
    system_prompt: str,
    user_prompt: str,
    images_b64: list[str],
) -> list[dict[str, Any]]:
    """Compose the message list with images on the first user turn.

    For multimodal streaming, the optimal ordering per Gemma docs is:
        1. system  (instructions)
        2. user    (images attached + minimal placeholder content)
        3. user    (the actual instruction / question)

    We collapse system into the system message and keep two user turns so
    the model attends to images before the instruction text.
    """
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": "[architecture diagram(s) attached]",
            "images": images_b64,
        },
        {"role": "user", "content": user_prompt},
    ]


async def stream_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    images_b64: list[str],
    temperature: float = 0.4,
    num_ctx: int = 8192,
    num_predict: int = 4096,
    json_mode: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Stream tokens from Ollama. Yields event dicts (see module docstring).

    The semaphore is acquired *before* the HTTP connection opens. If it's
    already held, this generator yields a single `busy` event and returns;
    callers should propagate that to the SSE stream so the client UI can
    show "model in use" without waiting silently.
    """
    if ollama_semaphore.locked():
        yield {"type": "busy", "message": "Another request is using the model"}
        # Still wait for the lock — callers expect to eventually proceed.

    async with ollama_semaphore:
        async for evt in _stream_impl(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            images_b64=images_b64,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict,
            json_mode=json_mode,
        ):
            yield evt


async def _stream_impl(
    *,
    system_prompt: str,
    user_prompt: str,
    images_b64: list[str],
    temperature: float,
    num_ctx: int,
    num_predict: int,
    json_mode: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    payload = {
        "model": settings.ollama_model,
        "stream": True,
        "keep_alive": settings.ollama_keep_alive,
        # `think: False` disables Gemma 4's reasoning/thinking mode (which
        # otherwise routes output into `message.thinking` and leaves
        # `message.content` empty). On non-thinking models like qwen2.5vl
        # this flag is silently ignored — safe either way.
        "think": False,
        "messages": _build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            images_b64=images_b64,
        ),
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    if json_mode:
        # Constrain output to valid JSON. Used by per-criterion scoring
        # where each call returns a small {compliance_pct, evidence, remarks}
        # object.
        payload["format"] = "json"

    started = time.monotonic()
    ttft_ms: float | None = None

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_host.rstrip('/')}/api/chat",
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    text = body.decode("utf-8", errors="replace")
                    code = _classify_error(resp.status_code, text)
                    yield {
                        "type": "error",
                        "code": code,
                        "message": f"Ollama returned {resp.status_code}: {text[:200]}",
                    }
                    return

                line_buf = ""
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    line_buf += chunk.decode("utf-8", errors="replace")
                    while "\n" in line_buf:
                        line, line_buf = line_buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            evt = json.loads(line)
                        except json.JSONDecodeError as exc:
                            logger.warning(
                                "ollama_client: dropped unparseable line: %r (%s)",
                                line[:120], exc,
                            )
                            continue

                        msg = evt.get("message") or {}
                        # Belt-and-braces: even with `think: False`, some
                        # Ollama / model combos still emit a `thinking`
                        # field. Treat it as ordinary content so we never
                        # silently drop output.
                        content = msg.get("content", "") or msg.get(
                            "thinking", ""
                        )
                        if content:
                            if ttft_ms is None:
                                ttft_ms = (time.monotonic() - started) * 1000
                            yield {"type": "token", "content": content}

                        if evt.get("done"):
                            total_ms = (time.monotonic() - started) * 1000
                            yield {
                                "type": "done",
                                "ttft_ms": int(ttft_ms or 0),
                                "total_ms": int(total_ms),
                                "eval_count": evt.get("eval_count"),
                                "prompt_eval_count": evt.get("prompt_eval_count"),
                            }
                            return
    except httpx.TimeoutException:
        yield {
            "type": "error",
            "code": "timeout",
            "message": "Ollama request timed out",
        }
    except httpx.HTTPError as exc:
        yield {
            "type": "error",
            "code": "upstream_unreachable",
            "message": f"Could not reach Ollama: {exc}",
        }


def _classify_error(status: int, body: str) -> str:
    body_lower = body.lower()
    if "out of memory" in body_lower or "cuda" in body_lower:
        return "vram_oom"
    if status == 404 and "model" in body_lower:
        return "model_missing"
    if status >= 500:
        return "upstream_5xx"
    return "upstream_4xx"


async def check_health() -> tuple[bool, bool, str | None]:
    """Ping Ollama. Returns (reachable, model_present, error_or_none)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_host.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return False, False, f"status {resp.status_code}"
            tags = resp.json().get("models", [])
            available = [m.get("name", "") for m in tags]
            model_present = settings.ollama_model in available or any(
                name.startswith(settings.ollama_model.split(":")[0]) for name in available
            )
            return True, model_present, None
    except httpx.HTTPError as exc:
        return False, False, str(exc)
