"""POST /analyze — run an analysis on a single architecture diagram.

Accepts multipart/form-data:
    image:        File (PNG | JPEG, ≤15 MB)
    mode:         'quick' | 'detailed' | 'persona' | 'user_driven'
    persona:      'data' | 'network' | 'security' | 'enterprise'  (mode=persona only)
    focus_areas:  comma-separated list (mode=detailed only, optional)
    user_prompt:  string (mode=user_driven only, required there)

Streams Server-Sent Events (`text/event-stream`) — see ollama_client.py
for the event shapes. The session is persisted to Postgres at start
(status=running) and updated to done/error when the stream completes.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, get_db
from app.models.db import Framework, Session
from app.models.requests import AnalysisMode, Persona, SessionStatus, SessionType
from app.ollama_client import stream_chat
from app.prompts import (
    ANALYZE_QUICK,
    build_compliance_prompt,
    build_persona_prompt,
    build_user_driven_prompt,
)
from app.prompts.analyze_detailed import build_detailed_prompt
from app.services.image_store import upsert_image
from app.utils.compliance_parser import (
    ComplianceStreamParser,
    compute_weighted_score,
)
from app.utils.docx_utils import (
    DocxExtractionError,
    extract_docx,
    is_docx,
)
from app.utils.image_utils import (
    ImageValidationError,
    ProcessedImage,
    validate_and_resize,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_focus_areas(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def _parse_framework_ids(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _process_upload(
    *, raw: bytes, content_type: str | None, filename: str | None
) -> tuple[ProcessedImage, str | None]:
    """Return (image, doc_text). For .docx uploads, extract the first
    embedded image + concatenated prose. For image uploads, run the normal
    validate_and_resize pipeline and return text=None.
    """
    if is_docx(content_type, filename):
        # Same byte cap as images — protects the docx parser from OOM.
        from app.config import settings as _settings  # local: avoid cycle
        if len(raw) > _settings.max_upload_bytes:
            raise HTTPException(
                400,
                f"Document exceeds max upload size "
                f"({len(raw):,} > {_settings.max_upload_bytes:,} bytes)",
            )
        try:
            extracted = extract_docx(raw)
        except DocxExtractionError as exc:
            raise HTTPException(400, str(exc))
        if not extracted.images:
            raise HTTPException(
                400,
                "The uploaded Word document does not contain any embedded "
                "images. Add at least one architecture diagram to the doc "
                "and try again.",
            )
        # First embedded image is treated as the primary diagram. Multi-image
        # docs aren't supported in v1 — we keep the rest of the pipeline
        # unchanged (single image_hash on Session).
        img_bytes, img_ct = extracted.images[0]
        try:
            processed = validate_and_resize(img_bytes, content_type=img_ct)
        except ImageValidationError as exc:
            raise HTTPException(
                400,
                f"First embedded image in the .docx failed validation: {exc}",
            )
        return processed, (extracted.text or None)

    # Plain image upload.
    try:
        processed = validate_and_resize(raw, content_type=content_type)
    except ImageValidationError as exc:
        raise HTTPException(400, str(exc))
    return processed, None


def _augment_user_msg(user_msg: str, doc_text: str | None) -> str:
    """If doc_text is set, prepend it as additional context for the model."""
    if not doc_text:
        return user_msg
    # Truncate very long docs to keep within Gemma's context budget. The
    # vision tile + system prompt + criteria already eat a chunk of the
    # 16k-token context; ~6000 chars of prose is plenty.
    snippet = doc_text[:6000]
    truncated_marker = "" if len(doc_text) <= 6000 else "\n\n[…document truncated]"
    return (
        "Additional context from the uploaded Word document (use alongside "
        "the diagram for your analysis):\n\n"
        f"{snippet}{truncated_marker}\n\n---\n\n{user_msg}"
    )


def _resolve_prompt(
    *,
    mode: AnalysisMode,
    persona: Persona | None,
    focus_areas: list[str] | None,
    user_prompt: str | None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt_for_model).

    The "user prompt for model" is the second user-message text; for modes
    other than user_driven it's a short instruction nudging the model to
    produce the structured output described in the system prompt.
    """
    if mode == AnalysisMode.QUICK:
        return ANALYZE_QUICK, "Produce the analysis as instructed."
    if mode == AnalysisMode.DETAILED:
        return (
            build_detailed_prompt(focus_areas),
            "Produce the detailed analysis as instructed.",
        )
    if mode == AnalysisMode.PERSONA:
        if not persona:
            raise HTTPException(400, "persona is required when mode=persona")
        return (
            build_persona_prompt(persona.value),
            "Produce the persona-specific analysis as instructed.",
        )
    if mode == AnalysisMode.USER_DRIVEN:
        if not user_prompt or not user_prompt.strip():
            raise HTTPException(
                400, "user_prompt is required when mode=user_driven"
            )
        return (
            build_user_driven_prompt(user_prompt),
            user_prompt.strip(),
        )
    raise HTTPException(400, f"Unknown mode: {mode}")


def _sse_event(payload: dict) -> bytes:
    """Encode a single SSE event line."""
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()


@router.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    mode: AnalysisMode = Form(...),
    persona: Persona | None = Form(None),
    focus_areas: str | None = Form(None),
    user_prompt: str | None = Form(None),
    framework_ids: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    raw = await image.read()
    processed, doc_text = _process_upload(
        raw=raw,
        content_type=image.content_type,
        filename=image.filename,
    )

    # Compliance mode runs N model calls (one per framework) and streams
    # framework-aware events. Diverges enough from the linear single-prompt
    # modes to warrant its own branch.
    if mode == AnalysisMode.COMPLIANCE:
        return await _run_compliance(
            processed=processed,
            doc_text=doc_text,
            framework_ids=_parse_framework_ids(framework_ids),
            user_prompt=user_prompt,
            db=db,
        )

    parsed_focus = _parse_focus_areas(focus_areas)
    system_prompt, user_msg = _resolve_prompt(
        mode=mode,
        persona=persona,
        focus_areas=parsed_focus,
        user_prompt=user_prompt,
    )
    user_msg = _augment_user_msg(user_msg, doc_text)

    # Persist the image (idempotent on hash) and a session row up-front so
    # the History sidebar can show it even while the stream is still
    # running.
    await upsert_image(db, processed)
    sess = Session(
        session_type=SessionType.ANALYZE.value,
        mode=mode.value,
        persona=persona.value if persona else None,
        focus_areas=parsed_focus,
        user_prompt=user_prompt,
        image_hash=processed.sha256,
        status=SessionStatus.RUNNING.value,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    session_id = sess.id

    logger.info(
        "analyze_started",
        extra={
            "session_id": session_id,
            "mode": mode.value,
            "persona": persona.value if persona else None,
            "focus_areas": parsed_focus,
            "image_bytes_in": len(raw),
            "image_bytes_resized": len(processed.resized_bytes),
            "image_hash_prefix": processed.sha256[:12],
        },
    )

    async def event_generator() -> AsyncIterator[bytes]:
        # Tell the client up-front which session we created.
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
                user_prompt=user_msg,
                images_b64=[processed.b64],
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
            # Client disconnected — record what we have and re-raise.
            client_disconnected = True
            raise
        finally:
            # Persist final state in a fresh session (the original `db` is
            # already closed once the streaming response detaches). This
            # MUST run even on cancellation so the History sidebar
            # doesn't show an orphaned `running` row forever.
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
            except Exception:  # noqa: BLE001 — never let DB errors break the response
                logger.exception("Failed to persist final session state")

            logger.info(
                "analyze_finished",
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
            "X-Accel-Buffering": "no",  # belt-and-braces for nginx
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ── Compliance mode ───────────────────────────────────────────────────────


_SSE_HEADERS = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


async def _run_compliance(
    *,
    processed,
    doc_text: str | None = None,
    framework_ids: list[str],
    user_prompt: str | None,
    db: AsyncSession,
) -> StreamingResponse:
    """Run multi-framework compliance analysis on the processed image.

    Strategy: persist a Session row up-front, then for each selected
    framework, invoke `stream_chat()` with a compliance prompt and feed the
    resulting tokens through ComplianceStreamParser to emit framework-aware
    SSE events. The full per-framework scorecards are accumulated and
    written to Session.scorecards in the finally block.
    """
    if not framework_ids:
        raise HTTPException(400, "At least one framework_id is required for mode=compliance")

    # Load all frameworks (with items) in a single query, preserve user-given
    # order but skip duplicates and unknown ids.
    stmt = (
        select(Framework)
        .where(Framework.id.in_(framework_ids))
        .options(selectinload(Framework.items))
    )
    rows = (await db.execute(stmt)).scalars().all()
    by_id = {fw.id: fw for fw in rows}
    seen: set[str] = set()
    ordered: list[Framework] = []
    for fid in framework_ids:
        if fid in by_id and fid not in seen:
            ordered.append(by_id[fid])
            seen.add(fid)
    if not ordered:
        raise HTTPException(404, "None of the supplied framework_ids exist")

    await upsert_image(db, processed)
    sess = Session(
        session_type=SessionType.ANALYZE.value,
        mode=AnalysisMode.COMPLIANCE.value,
        user_prompt=user_prompt,
        image_hash=processed.sha256,
        status=SessionStatus.RUNNING.value,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    session_id = sess.id

    logger.info(
        "compliance_started",
        extra={
            "session_id": session_id,
            "framework_count": len(ordered),
            "framework_ids": [fw.id for fw in ordered],
            "image_bytes_resized": len(processed.resized_bytes),
        },
    )

    async def event_generator() -> AsyncIterator[bytes]:
        yield _sse_event({"type": "session_created", "id": session_id})

        scorecards: list[dict] = []
        ttft_ms_overall: int | None = None
        total_ms_overall: int = 0
        had_error = False
        error_message: str | None = None
        client_disconnected = False
        completed_normally = False

        try:
            for fw in ordered:
                # Map the framework's items to the [idx]-keyed list the
                # prompt + parser expect. Sort_order should already be
                # respected by the relationship's order_by, but be defensive.
                fw_items = sorted(fw.items, key=lambda it: it.sort_order)
                items_for_prompt = [
                    {
                        "criteria": it.criteria,
                        "weight_planned": float(it.weight_planned or 0),
                    }
                    for it in fw_items
                ]
                # Per-framework collection bag for the saved scorecard.
                row_by_idx: dict[int, dict] = {}

                yield _sse_event(
                    {
                        "type": "framework_started",
                        "framework_id": fw.id,
                        "framework_name": fw.name,
                        "item_count": len(fw_items),
                        "items": [
                            {
                                "idx": i,
                                "framework_item_id": it.id,
                                "criteria": it.criteria,
                                "weight_planned": float(it.weight_planned or 0),
                            }
                            for i, it in enumerate(fw_items)
                        ],
                    }
                )

                system_prompt = build_compliance_prompt(
                    framework_name=fw.name,
                    items=items_for_prompt,
                )
                # The "user" message is a short nudge; the heavy lifting is
                # in the system prompt + the framework's criteria block.
                user_msg = (
                    "Score the architecture diagram against the criteria above. "
                    "Output ONLY the two delimited sections."
                )
                user_msg = _augment_user_msg(user_msg, doc_text)

                parser = ComplianceStreamParser()
                async for evt in stream_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_msg,
                    images_b64=[processed.b64],
                    temperature=0.2,
                    num_ctx=16384,
                    num_predict=8000,
                ):
                    et = evt["type"]
                    if et == "token":
                        for parsed in parser.feed(evt["content"]):
                            if parsed["type"] == "narrative_token":
                                yield _sse_event(
                                    {
                                        "type": "narrative_token",
                                        "framework_id": fw.id,
                                        "content": parsed["content"],
                                    }
                                )
                            elif parsed["type"] == "scorecard_row":
                                idx = parsed["idx"]
                                if 0 <= idx < len(fw_items):
                                    src = fw_items[idx]
                                    row_by_idx[idx] = {
                                        "framework_item_id": src.id,
                                        "criteria": src.criteria,
                                        "weight_planned": float(src.weight_planned or 0),
                                        "compliance_pct": parsed["compliance_pct"],
                                        "remarks": parsed["remarks"],
                                    }
                                    yield _sse_event(
                                        {
                                            "type": "scorecard_row",
                                            "framework_id": fw.id,
                                            "idx": idx,
                                            "compliance_pct": parsed["compliance_pct"],
                                            "remarks": parsed["remarks"],
                                        }
                                    )
                    elif et == "done":
                        # Per-framework done: flush parser, fill missing rows,
                        # compute weighted score, emit framework_done.
                        for parsed in parser.flush():
                            yield _sse_event(
                                {
                                    "type": "narrative_token",
                                    "framework_id": fw.id,
                                    "content": parsed["content"],
                                }
                            )
                        # Backfill any criteria the model didn't score with
                        # null/N-A so the saved scorecard is complete.
                        items_full = []
                        for i, src in enumerate(fw_items):
                            row = row_by_idx.get(i) or {
                                "framework_item_id": src.id,
                                "criteria": src.criteria,
                                "weight_planned": float(src.weight_planned or 0),
                                "compliance_pct": None,
                                "remarks": None,
                            }
                            items_full.append(row)
                        weighted = compute_weighted_score(items_full)
                        scorecards.append(
                            {
                                "framework_id": fw.id,
                                "framework_name": fw.name,
                                "narrative_markdown": parser.narrative_text,
                                "weighted_score": round(weighted, 2),
                                "items": items_full,
                            }
                        )
                        if ttft_ms_overall is None:
                            ttft_ms_overall = evt.get("ttft_ms")
                        total_ms_overall += int(evt.get("total_ms") or 0)
                        yield _sse_event(
                            {
                                "type": "framework_done",
                                "framework_id": fw.id,
                                "weighted_score": round(weighted, 2),
                            }
                        )
                    elif et == "error":
                        had_error = True
                        error_message = evt.get("message")
                        yield _sse_event(evt)
                        break  # stop processing further frameworks
                    elif et == "busy":
                        yield _sse_event(evt)
                    # else: silently drop unknown event types

                if had_error:
                    break

            yield _sse_event(
                {
                    "type": "done",
                    "ttft_ms": ttft_ms_overall or 0,
                    "total_ms": total_ms_overall,
                }
            )
            completed_normally = True
        except (GeneratorExit, asyncio.CancelledError):
            client_disconnected = True
            raise
        finally:
            try:
                async with AsyncSessionLocal() as fresh_db:
                    row = await fresh_db.get(Session, session_id)
                    if row is not None:
                        row.scorecards = scorecards or None
                        row.completed_at = datetime.now(timezone.utc)
                        row.ttft_ms = ttft_ms_overall
                        row.total_ms = total_ms_overall or None
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
                logger.exception("Failed to persist compliance session state")

            logger.info(
                "compliance_finished",
                extra={
                    "session_id": session_id,
                    "status": "error" if had_error or client_disconnected else "done",
                    "frameworks_completed": len(scorecards),
                    "total_ms": total_ms_overall,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
