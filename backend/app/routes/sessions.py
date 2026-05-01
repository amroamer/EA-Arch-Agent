"""GET /sessions — paginated list and detail view for the History sidebar.

Also: PUT /sessions/{id}/scorecards — save user edits to compliance-mode
scorecard results (compliance_pct + remarks per criterion). The server
re-computes the weighted_score so it stays consistent with the saved values.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import Session
from app.models.responses import SessionDetail, SessionListItem
from app.utils.compliance_parser import compute_weighted_score

router = APIRouter()


# ── Compliance scorecard edit schemas ─────────────────────────────────────


class ScorecardItemPatch(BaseModel):
    framework_item_id: str | None = None
    criteria: str
    weight_planned: float = Field(0.0, ge=0, le=100)
    compliance_pct: float | None = Field(None, ge=0, le=100)
    remarks: str | None = None


class ScorecardPatch(BaseModel):
    framework_id: str
    framework_name: str
    narrative_markdown: str | None = None
    items: list[ScorecardItemPatch] = Field(default_factory=list)


class ScorecardsBody(BaseModel):
    scorecards: list[ScorecardPatch]


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[SessionListItem]:
    stmt = (
        select(Session)
        .order_by(desc(Session.created_at))
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        SessionListItem(
            id=r.id,
            session_type=r.session_type,
            mode=r.mode,
            persona=r.persona,
            prompt_preview=r.prompt_preview,
            status=r.status,
            created_at=r.created_at,
            completed_at=r.completed_at,
            total_ms=r.total_ms,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    row = await db.get(Session, session_id)
    if row is None:
        raise HTTPException(404, "Session not found")
    return SessionDetail.model_validate(row)


@router.put("/sessions/{session_id}/scorecards", response_model=SessionDetail)
async def save_scorecards(
    session_id: str,
    body: ScorecardsBody,
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    """Replace the session's scorecards with the provided edits.

    Validates that compliance_pct is one of {0, 50, 100, null}, recomputes
    weighted_score per framework, and writes the JSON back atomically.
    """
    row = await db.get(Session, session_id)
    if row is None:
        raise HTTPException(404, "Session not found")
    if row.mode != "compliance":
        raise HTTPException(
            400, "Only compliance-mode sessions have scorecards to save"
        )

    cleaned: list[dict] = []
    for sc in body.scorecards:
        items: list[dict] = []
        for it in sc.items:
            # Snap any non-categorical numeric value to {0,50,100}; preserve
            # None (means "Not Applicable" — different from "0% compliant").
            pct = it.compliance_pct
            if pct is not None and pct not in {0, 50, 100}:
                pct = 0 if pct < 25 else (50 if pct < 75 else 100)
            remarks = (it.remarks or "").strip() or None
            items.append(
                {
                    "framework_item_id": it.framework_item_id,
                    "criteria": it.criteria,
                    "weight_planned": float(it.weight_planned or 0),
                    "compliance_pct": pct,
                    "remarks": remarks,
                }
            )
        weighted = compute_weighted_score(items)
        cleaned.append(
            {
                "framework_id": sc.framework_id,
                "framework_name": sc.framework_name,
                "narrative_markdown": sc.narrative_markdown,
                "weighted_score": round(weighted, 2),
                "items": items,
            }
        )

    row.scorecards = cleaned
    await db.commit()
    await db.refresh(row)
    return SessionDetail.model_validate(row)
