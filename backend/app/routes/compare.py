"""POST /compare — compare current vs reference architecture.

Accepts multipart/form-data:
    current_image:    File (PNG | JPEG)
    reference_image:  File (PNG | JPEG)
    user_prompt:      string (required)

Streams SSE events identical in shape to /analyze.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.db import Session
from app.models.requests import SessionStatus, SessionType
from app.ollama_client import stream_chat
from app.prompts import build_compare_prompt
from app.services.image_store import upsert_image
from app.services.llm_config import fetch_active_llm_config
from app.utils.image_utils import ImageValidationError, validate_and_resize

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse_event(payload: dict) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()


@router.post("/compare")
async def compare(
    current_image: UploadFile = File(...),
    reference_image: UploadFile = File(...),
    user_prompt: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if not user_prompt or not user_prompt.strip():
        raise HTTPException(400, "user_prompt is required")

    try:
        cur_raw = await current_image.read()
        ref_raw = await reference_image.read()
        cur = validate_and_resize(
            cur_raw, content_type=current_image.content_type
        )
        ref = validate_and_resize(
            ref_raw, content_type=reference_image.content_type
        )
    except ImageValidationError as exc:
        raise HTTPException(400, str(exc))

    system_prompt = build_compare_prompt(user_prompt)

    await upsert_image(db, cur)
    await upsert_image(db, ref)
    sess = Session(
        session_type=SessionType.COMPARE.value,
        user_prompt=user_prompt,
        image_hash=cur.sha256,
        reference_image_hash=ref.sha256,
        status=SessionStatus.RUNNING.value,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    session_id = sess.id

    # Resolve the user's saved LLM config (Settings → LLM Model).
    active_llm = await fetch_active_llm_config(db)

    async def event_generator() -> AsyncIterator[bytes]:
        yield _sse_event({"type": "session_created", "id": session_id})

        collected: list[str] = []
        ttft_ms: int | None = None
        total_ms: int | None = None
        had_error: bool = False
        error_message: str | None = None
        client_disconnected = False
        completed_normally = False

        try:
            async for evt in stream_chat(
                system_prompt=system_prompt,
                user_prompt="Produce the comparison and roadmap as instructed.",
                images_b64=[cur.b64, ref.b64],
                **active_llm.to_chat_kwargs(),
            ):
                if evt["type"] == "token":
                    collected.append(evt["content"])
                elif evt["type"] == "done":
                    ttft_ms = evt.get("ttft_ms")
                    total_ms = evt.get("total_ms")
                elif evt["type"] == "error":
                    had_error = True
                    error_message = evt.get("message")
                yield _sse_event(evt)
            completed_normally = True
        except (GeneratorExit, asyncio.CancelledError):
            client_disconnected = True
            raise
        finally:
            try:
                async with AsyncSessionLocal() as fresh_db:
                    row = await fresh_db.get(Session, session_id)
                    if row is not None:
                        row.response_markdown = (
                            "".join(collected) if collected else None
                        )
                        row.completed_at = datetime.now(timezone.utc)
                        row.ttft_ms = ttft_ms
                        row.total_ms = total_ms
                        if had_error:
                            row.status = SessionStatus.ERROR.value
                            row.error_message = error_message
                        elif client_disconnected and not completed_normally:
                            row.status = SessionStatus.ERROR.value
                            row.error_message = "Client disconnected before completion"
                        else:
                            row.status = SessionStatus.DONE.value
                        await fresh_db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to persist final session state")

            logger.info(
                "compare_finished",
                extra={
                    "session_id": session_id,
                    "status": (
                        "error"
                        if had_error or client_disconnected
                        else "done"
                    ),
                    "client_disconnected": client_disconnected,
                    "ttft_ms": ttft_ms,
                    "total_ms": total_ms,
                    "response_chars": sum(len(c) for c in collected),
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
