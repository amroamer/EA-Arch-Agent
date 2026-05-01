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
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, get_db
from app.models.db import Framework, Session
from app.models.requests import (
    AnalysisMode,
    Persona,
    ScoringMode,
    SessionStatus,
    SessionType,
)
from app.ollama_client import stream_chat
from app.prompts import (
    build_compliance_prompt,
    build_persona_prompt,
    build_user_driven_prompt,
)
from app.prompts.analyze_detailed import build_detailed_prompt
from app.prompts.analyze_quick import build_quick_prompt
from app.prompts.store import fetch_template
from app.services.image_store import upsert_image
from app.utils.compliance_parser import (
    ComplianceStreamParser,
    compute_weighted_score,
)
from app.utils.compliance_rules import _enforce_evidence_rule
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
) -> tuple[ProcessedImage | None, str | None]:
    """Return (image, doc_text).

    - .docx with embedded image(s): use the first as the diagram + extract
      text as additional context.
    - .docx with text only (no images): image is None, doc_text carries
      the prose. Caller drives a text-only analysis.
    - .docx with neither images nor non-trivial text: 400.
    - Image upload (PNG/JPEG): normal validate_and_resize, text=None.
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

        text = (extracted.text or "").strip() or None

        if not extracted.images and not text:
            raise HTTPException(
                400,
                "The uploaded Word document is empty: it has neither an "
                "embedded image nor any prose. Add an architecture diagram "
                "or describe the architecture in text and try again.",
            )

        if not extracted.images:
            # Text-only path: model analyzes the prose without a vision input.
            return None, text

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
        return processed, text

    # Plain image upload.
    try:
        processed = validate_and_resize(raw, content_type=content_type)
    except ImageValidationError as exc:
        raise HTTPException(400, str(exc))
    return processed, None


# Cap on the prose context we send to the model. 30 000 chars ≈ ~7.5k
# tokens — comfortable alongside the criteria block + system prompt at
# num_ctx=16384, captures most ADR tables and early operational sections
# of a real SAD, and keeps qwen2.5vl 7B in its fast regime.
# Empirically: 40k cap at num_ctx=32768 balloons single-framework calls
# from ~20s to ~4 minutes — not worth the marginal extra coverage.
# Structured extraction (markdown headings, labelled tables) means the
# leading 30k carries more signal than the old flat 6k.
_DOC_TEXT_CHAR_CAP = 30_000


def _augment_user_msg(user_msg: str, doc_text: str | None) -> str:
    """If doc_text is set, prepend it as additional context for the model."""
    if not doc_text:
        return user_msg
    if len(doc_text) <= _DOC_TEXT_CHAR_CAP:
        snippet = doc_text
        truncated_marker = ""
    else:
        snippet = doc_text[:_DOC_TEXT_CHAR_CAP]
        truncated_marker = (
            f"\n\n[…document truncated — "
            f"{_DOC_TEXT_CHAR_CAP:,} of {len(doc_text):,} chars shown]"
        )
    return (
        "Additional context from the uploaded Word document (use alongside "
        "the diagram for your analysis):\n\n"
        f"{snippet}{truncated_marker}\n\n---\n\n{user_msg}"
    )


def _ctx_for(doc_text: str | None) -> int:
    """Pick num_ctx based on whether we're augmenting with prose context.

    Image-only flows fit comfortably in the default 8k. With doc text
    (capped at ~5k tokens) plus criteria + system prompt, 16k is enough
    headroom and keeps qwen2.5vl 7B in its fast regime.
    """
    return 16_384 if doc_text else 8_192


async def _resolve_prompt(
    *,
    mode: AnalysisMode,
    persona: Persona | None,
    focus_areas: list[str] | None,
    user_prompt: str | None,
    db: AsyncSession,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt_for_model).

    Each mode fetches its template from prompt_overrides (DB) with the
    Python default as fallback, so user customisations from
    Settings → Prompts take effect on the next request.

    The "user prompt for model" is the second user-message text; for modes
    other than user_driven it's a short instruction nudging the model to
    produce the structured output described in the system prompt.
    """
    if mode == AnalysisMode.QUICK:
        tpl = await fetch_template(db, "analyze_quick")
        return build_quick_prompt(template=tpl), "Produce the analysis as instructed."
    if mode == AnalysisMode.DETAILED:
        tpl = await fetch_template(db, "analyze_detailed")
        return (
            build_detailed_prompt(focus_areas, template=tpl),
            "Produce the detailed analysis as instructed.",
        )
    if mode == AnalysisMode.PERSONA:
        if not persona:
            raise HTTPException(400, "persona is required when mode=persona")
        tpl = await fetch_template(db, "analyze_persona")
        return (
            build_persona_prompt(persona.value, template=tpl),
            "Produce the persona-specific analysis as instructed.",
        )
    if mode == AnalysisMode.USER_DRIVEN:
        if not user_prompt or not user_prompt.strip():
            raise HTTPException(
                400, "user_prompt is required when mode=user_driven"
            )
        tpl = await fetch_template(db, "analyze_user_driven")
        return (
            build_user_driven_prompt(user_prompt, template=tpl),
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
    scoring_mode: ScoringMode = Form(ScoringMode.SINGLE_PASS),
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
    # modes to warrant its own branch. The scoring_mode flag picks between
    # the original single-pass orchestrator and the new per-criterion one.
    if mode == AnalysisMode.COMPLIANCE:
        runner = (
            _run_compliance_per_criterion
            if scoring_mode == ScoringMode.PER_CRITERION
            else _run_compliance
        )
        return await runner(
            processed=processed,
            doc_text=doc_text,
            framework_ids=_parse_framework_ids(framework_ids),
            user_prompt=user_prompt,
            db=db,
        )

    parsed_focus = _parse_focus_areas(focus_areas)
    system_prompt, user_msg = await _resolve_prompt(
        mode=mode,
        persona=persona,
        focus_areas=parsed_focus,
        user_prompt=user_prompt,
        db=db,
    )
    user_msg = _augment_user_msg(user_msg, doc_text)

    # Persist the image (idempotent on hash) and a session row up-front so
    # the History sidebar can show it even while the stream is still
    # running. For text-only docx (no embedded image), processed is None
    # and image_hash stays NULL.
    if processed is not None:
        await upsert_image(db, processed)
    sess = Session(
        session_type=SessionType.ANALYZE.value,
        mode=mode.value,
        persona=persona.value if persona else None,
        focus_areas=parsed_focus,
        user_prompt=user_prompt,
        image_hash=processed.sha256 if processed else None,
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
            "image_bytes_resized": len(processed.resized_bytes) if processed else 0,
            "image_hash_prefix": processed.sha256[:12] if processed else None,
            "doc_text_chars": len(doc_text) if doc_text else 0,
            "doc_truncated": bool(doc_text and len(doc_text) > _DOC_TEXT_CHAR_CAP),
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
                images_b64=[processed.b64] if processed else [],
                num_ctx=_ctx_for(doc_text),
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
    processed: ProcessedImage | None,
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

    if processed is not None:
        await upsert_image(db, processed)
    sess = Session(
        session_type=SessionType.ANALYZE.value,
        mode=AnalysisMode.COMPLIANCE.value,
        user_prompt=user_prompt,
        image_hash=processed.sha256 if processed else None,
        status=SessionStatus.RUNNING.value,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    session_id = sess.id

    # Resolve the compliance template ONCE per request (not per framework).
    # The template is identical across frameworks within a single run; the
    # framework-specific bits are injected via .format() in the builder.
    compliance_template = await fetch_template(db, "analyze_compliance")

    logger.info(
        "compliance_started",
        extra={
            "session_id": session_id,
            "framework_count": len(ordered),
            "framework_ids": [fw.id for fw in ordered],
            "image_bytes_resized": len(processed.resized_bytes) if processed else 0,
            "doc_text_chars": len(doc_text) if doc_text else 0,
            "doc_truncated": bool(doc_text and len(doc_text) > _DOC_TEXT_CHAR_CAP),
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
                    template=compliance_template,
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
                    images_b64=[processed.b64] if processed else [],
                    temperature=0.2,
                    num_ctx=16_384,
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


# ── Compliance per-criterion mode ─────────────────────────────────────────


# Matches stable criterion IDs at the start of criteria text:
#   "Q1-S-INF-1.1: Does the infrastructure ..." → "Q1-S-INF-1.1"
#   "Q12-S-APP-7.1:Can the application scale..." → "Q12-S-APP-7.1"
_CRITERION_ID_RE = re.compile(r"^(Q\d+(?:-[A-Z0-9]+)+(?:\.\d+)?)", re.IGNORECASE)


def _extract_criterion_id(criteria: str, *, fallback: str) -> str:
    """Pull the leading 'Q5-S-INF-1.3' from the criterion text, or fall back."""
    if not criteria:
        return fallback
    m = _CRITERION_ID_RE.match(criteria.strip())
    return m.group(1) if m else fallback


def _strip_criterion_id_prefix(criteria: str) -> str:
    """Remove the leading ID + colon so the model sees just the question."""
    if not criteria:
        return ""
    s = criteria.strip()
    m = _CRITERION_ID_RE.match(s)
    if not m:
        return s
    rest = s[m.end():].lstrip()
    if rest.startswith(":"):
        rest = rest[1:].lstrip()
    return rest


def _render_verdicts_block(verdicts: list[dict]) -> str:
    """Format the per-criterion verdicts for the synthesis prompt.

    One line per verdict, e.g.:
      [Q1-S-INF-1.1] weight 25 — Compliant — evidence: §9.3 — Architecture …
    """
    lines: list[str] = []
    for v in verdicts:
        cid = v.get("criterion_id") or "?"
        weight = v.get("weight_planned", 0)
        pct = v.get("compliance_pct")
        label = (
            "Compliant" if pct == 100
            else "Partial" if pct == 50
            else "Not Compliant" if pct == 0
            else "N/A"
        )
        evidence = (v.get("evidence") or "").strip() or "none"
        remarks = (v.get("remarks") or "").strip()
        lines.append(
            f"[{cid}] weight {weight:g} — {label} — evidence: {evidence} — {remarks}"
        )
    return "\n".join(lines)


async def _score_one_criterion(
    *,
    template: str,
    framework_name: str,
    criterion_id: str,
    criterion_text: str,
    document_text: str,
    image_b64: str | None,
) -> dict:
    """Make ONE Ollama call for ONE criterion. Returns the verdict dict
    {compliance_pct, evidence, remarks} after evidence-enforcement.

    Strategy:
      1. Try with `format: "json"` — model emits a strict JSON object.
      2. If parse fails, retry once WITHOUT json_mode and JSON-extract from
         the text response.
      3. If both fail, return a structured 'parse_failed' verdict so the
         framework run can continue (the row gets compliance_pct=null +
         a remarks note).
    """
    system_prompt = template.format(
        framework_name=framework_name,
        criterion_id=criterion_id,
        criterion_text=criterion_text,
        document_text=document_text or "(no document text provided)",
    )
    user_msg = "Score this criterion. Output ONLY the JSON object."
    images = [image_b64] if image_b64 else []

    async def _collect(json_mode: bool) -> str:
        pieces: list[str] = []
        async for evt in stream_chat(
            system_prompt=system_prompt,
            user_prompt=user_msg,
            images_b64=images,
            temperature=0.1,
            num_ctx=16_384,
            num_predict=512,  # ~150-token JSON object — plenty
            json_mode=json_mode,
        ):
            if evt["type"] == "token":
                pieces.append(evt["content"])
            elif evt["type"] == "error":
                raise RuntimeError(evt.get("message") or "ollama error")
            elif evt["type"] == "done":
                break
        return "".join(pieces).strip()

    def _parse_or_extract(raw: str) -> dict | None:
        """Try strict JSON first; on failure, scan for the first {...} block."""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None

    raw = ""
    parsed: dict | None = None
    try:
        raw = await _collect(json_mode=True)
        parsed = _parse_or_extract(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("per-criterion json_mode call failed: %s", exc)

    if parsed is None:
        try:
            raw = await _collect(json_mode=False)
            parsed = _parse_or_extract(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("per-criterion text-mode retry failed: %s", exc)

    if not isinstance(parsed, dict):
        # Hard failure — return a sentinel verdict so the orchestrator can
        # continue and the row shows as un-scored with a clear note.
        return {
            "compliance_pct": None,
            "evidence": "parse_failed",
            "remarks": (
                "Server could not parse the model's response into a JSON "
                "verdict. Re-run to retry. (raw: "
                f"{(raw or '')[:120]!r})"
            ),
        }

    # Normalise the three expected fields.
    pct = parsed.get("compliance_pct")
    if pct is not None and pct not in {0, 50, 100}:
        # Snap non-categorical numeric values to {0,50,100}.
        try:
            pct_num = float(pct)
            pct = 0 if pct_num < 25 else (50 if pct_num < 75 else 100)
        except (TypeError, ValueError):
            pct = None
    evidence = parsed.get("evidence")
    if not isinstance(evidence, str):
        evidence = "" if evidence is None else str(evidence)
    remarks = parsed.get("remarks")
    if not isinstance(remarks, str):
        remarks = "" if remarks is None else str(remarks)

    verdict = {
        "compliance_pct": pct,
        "evidence": evidence.strip(),
        "remarks": remarks.strip(),
    }
    return _enforce_evidence_rule(verdict)


async def _run_compliance_per_criterion(
    *,
    processed: ProcessedImage | None,
    doc_text: str | None = None,
    framework_ids: list[str],
    user_prompt: str | None,
    db: AsyncSession,
) -> StreamingResponse:
    """Per-criterion compliance orchestrator.

    For each framework: emit framework_started; then for each criterion
    emit criterion_started → call Ollama → emit criterion_done. After all
    criteria are scored, run ONE synthesis call streaming narrative_token
    events. Then emit framework_done with the full scorecard payload.
    """
    if not framework_ids:
        raise HTTPException(
            400, "At least one framework_id is required for mode=compliance"
        )

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

    if processed is not None:
        await upsert_image(db, processed)
    sess = Session(
        session_type=SessionType.ANALYZE.value,
        mode=AnalysisMode.COMPLIANCE.value,
        user_prompt=user_prompt,
        image_hash=processed.sha256 if processed else None,
        status=SessionStatus.RUNNING.value,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    session_id = sess.id

    # Resolve both templates ONCE per request.
    per_criterion_template = await fetch_template(db, "compliance_per_criterion_v1")
    synthesis_template = await fetch_template(db, "compliance_synthesis_v1")

    # Truncate the doc text the same way the single-pass mode does.
    doc_for_prompt = ""
    if doc_text:
        if len(doc_text) <= _DOC_TEXT_CHAR_CAP:
            doc_for_prompt = doc_text
        else:
            doc_for_prompt = (
                doc_text[:_DOC_TEXT_CHAR_CAP]
                + f"\n\n[…document truncated — {_DOC_TEXT_CHAR_CAP:,} of {len(doc_text):,} chars shown]"
            )

    logger.info(
        "compliance_per_criterion_started",
        extra={
            "session_id": session_id,
            "framework_count": len(ordered),
            "framework_ids": [fw.id for fw in ordered],
            "image_bytes_resized": len(processed.resized_bytes) if processed else 0,
            "doc_text_chars": len(doc_text) if doc_text else 0,
            "doc_truncated": bool(doc_text and len(doc_text) > _DOC_TEXT_CHAR_CAP),
        },
    )

    async def event_generator() -> AsyncIterator[bytes]:
        yield _sse_event({"type": "session_created", "id": session_id})

        scorecards: list[dict] = []
        had_error = False
        error_message: str | None = None
        client_disconnected = False
        completed_normally = False
        run_started = datetime.now(timezone.utc)

        try:
            for fw in ordered:
                fw_items = sorted(fw.items, key=lambda it: it.sort_order)
                # Build the prompt-facing items list, with criterion_id
                # extracted from the prefix and a clean question text.
                prepared = []
                for i, src in enumerate(fw_items):
                    cid = _extract_criterion_id(src.criteria, fallback=src.id[:8])
                    prepared.append(
                        {
                            "idx": i,
                            "framework_item_id": src.id,
                            "criterion_id": cid,
                            "criteria": src.criteria,
                            "criterion_text": _strip_criterion_id_prefix(src.criteria),
                            "weight_planned": float(src.weight_planned or 0),
                        }
                    )

                yield _sse_event(
                    {
                        "type": "framework_started",
                        "framework_id": fw.id,
                        "framework_name": fw.name,
                        "total_criteria": len(prepared),
                        # Backward-compat: include the same shape single_pass
                        # uses, plus the new criterion_id field.
                        "items": [
                            {
                                "idx": p["idx"],
                                "framework_item_id": p["framework_item_id"],
                                "criterion_id": p["criterion_id"],
                                "criteria": p["criteria"],
                                "weight_planned": p["weight_planned"],
                            }
                            for p in prepared
                        ],
                    }
                )

                verdicts: list[dict] = []
                for p in prepared:
                    yield _sse_event(
                        {
                            "type": "criterion_started",
                            "framework_id": fw.id,
                            "idx": p["idx"],
                            "criterion_id": p["criterion_id"],
                        }
                    )

                    # The actual model call. Sequential — Ollama serialises.
                    verdict = await _score_one_criterion(
                        template=per_criterion_template,
                        framework_name=fw.name,
                        criterion_id=p["criterion_id"],
                        criterion_text=p["criterion_text"] or p["criteria"],
                        document_text=doc_for_prompt,
                        image_b64=processed.b64 if processed else None,
                    )

                    yield _sse_event(
                        {
                            "type": "criterion_done",
                            "framework_id": fw.id,
                            "idx": p["idx"],
                            "criterion_id": p["criterion_id"],
                            "compliance_pct": verdict["compliance_pct"],
                            "evidence": verdict.get("evidence") or None,
                            "remarks": verdict.get("remarks") or None,
                        }
                    )

                    verdicts.append(
                        {
                            **p,
                            "compliance_pct": verdict["compliance_pct"],
                            "evidence": verdict.get("evidence") or None,
                            "remarks": verdict.get("remarks") or None,
                        }
                    )

                # ── Synthesis pass — one streaming call per framework ──
                synth_prompt = synthesis_template.format(
                    framework_name=fw.name,
                    verdicts_block=_render_verdicts_block(verdicts),
                )
                narrative_acc: list[str] = []
                async for evt in stream_chat(
                    system_prompt=synth_prompt,
                    user_prompt="Produce the narrative as instructed.",
                    images_b64=[],  # synthesis doesn't need the image
                    temperature=0.3,
                    num_ctx=16_384,
                    num_predict=2_000,
                ):
                    et = evt["type"]
                    if et == "token":
                        narrative_acc.append(evt["content"])
                        yield _sse_event(
                            {
                                "type": "narrative_token",
                                "framework_id": fw.id,
                                "content": evt["content"],
                            }
                        )
                    elif et == "error":
                        # Synthesis failed — keep the scorecard, skip the
                        # narrative for this framework.
                        logger.warning(
                            "synthesis_error",
                            extra={
                                "framework_id": fw.id,
                                "message": evt.get("message"),
                            },
                        )
                        break
                    elif et == "done":
                        break

                # Build the saved scorecard items (same shape as single_pass
                # plus an `evidence` field per row).
                items_full = []
                for v in verdicts:
                    items_full.append(
                        {
                            "framework_item_id": v["framework_item_id"],
                            "criteria": v["criteria"],
                            "weight_planned": v["weight_planned"],
                            "compliance_pct": v["compliance_pct"],
                            "evidence": v.get("evidence"),
                            "remarks": v.get("remarks"),
                        }
                    )
                weighted = compute_weighted_score(items_full)
                scorecard = {
                    "framework_id": fw.id,
                    "framework_name": fw.name,
                    "narrative_markdown": "".join(narrative_acc).strip() or None,
                    "weighted_score": round(weighted, 2),
                    "items": items_full,
                }
                scorecards.append(scorecard)

                yield _sse_event(
                    {
                        "type": "framework_done",
                        "framework_id": fw.id,
                        "weighted_score": round(weighted, 2),
                        "scorecard": scorecard,
                    }
                )

            yield _sse_event({"type": "done"})
            completed_normally = True
        except (GeneratorExit, asyncio.CancelledError):
            client_disconnected = True
            raise
        except Exception as exc:  # noqa: BLE001
            had_error = True
            error_message = str(exc)
            logger.exception("per-criterion compliance run failed")
            yield _sse_event({"type": "error", "message": error_message})
        finally:
            try:
                async with AsyncSessionLocal() as fresh_db:
                    row = await fresh_db.get(Session, session_id)
                    if row is not None:
                        row.scorecards = scorecards or None
                        row.completed_at = datetime.now(timezone.utc)
                        row.total_ms = int(
                            (datetime.now(timezone.utc) - run_started).total_seconds()
                            * 1000
                        )
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
                logger.exception("Failed to persist per-criterion session state")

            logger.info(
                "compliance_per_criterion_finished",
                extra={
                    "session_id": session_id,
                    "status": "error" if had_error or client_disconnected else "done",
                    "frameworks_completed": len(scorecards),
                    "total_criteria_scored": sum(
                        len(sc["items"]) for sc in scorecards
                    ),
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
