"""CRUD for EA compliance frameworks (Settings page).

Frameworks are simple aggregates: a Framework owns a list of items.
The PUT endpoint replaces the entire items list atomically so the
frontend can save the whole table in one request without tracking
per-row dirty state.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.db import Framework, FrameworkItem
from app.models.framework_schemas import (
    FrameworkDetail,
    FrameworkItemBase,
    FrameworkSummary,
    FrameworkUpsert,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────


def _replace_items(
    framework: Framework, items: list[FrameworkItemBase]
) -> None:
    """Replace the framework's items list. SQLAlchemy will issue
    DELETE + INSERTs against the cascade='delete-orphan' relationship."""
    framework.items = [
        FrameworkItem(
            criteria=it.criteria,
            weight_planned=it.weight_planned,
            weight_actual=it.weight_actual,
            compliance_pct=it.compliance_pct,
            remarks=it.remarks,
            sort_order=idx if it.sort_order == 0 else it.sort_order,
        )
        for idx, it in enumerate(items)
    ]


# ── Routes ─────────────────────────────────────────────────────────────


@router.get("/frameworks", response_model=list[FrameworkSummary])
async def list_frameworks(
    db: AsyncSession = Depends(get_db),
) -> list[FrameworkSummary]:
    """All frameworks, newest first, with item counts."""
    item_count = (
        select(
            FrameworkItem.framework_id,
            func.count(FrameworkItem.id).label("count"),
        )
        .group_by(FrameworkItem.framework_id)
        .subquery()
    )
    stmt = (
        select(Framework, func.coalesce(item_count.c.count, 0))
        .outerjoin(item_count, Framework.id == item_count.c.framework_id)
        .order_by(desc(Framework.updated_at))
    )
    rows = (await db.execute(stmt)).all()
    return [
        FrameworkSummary(
            id=fw.id,
            name=fw.name,
            description=fw.description,
            created_at=fw.created_at,
            updated_at=fw.updated_at,
            item_count=int(count),
        )
        for fw, count in rows
    ]


@router.post("/frameworks", response_model=FrameworkDetail, status_code=201)
async def create_framework(
    body: FrameworkUpsert,
    db: AsyncSession = Depends(get_db),
) -> FrameworkDetail:
    fw = Framework(name=body.name.strip(), description=body.description)
    _replace_items(fw, body.items)
    db.add(fw)
    await db.commit()
    await db.refresh(fw, attribute_names=["items"])
    return FrameworkDetail.model_validate(fw)


@router.get("/frameworks/{framework_id}", response_model=FrameworkDetail)
async def get_framework(
    framework_id: str,
    db: AsyncSession = Depends(get_db),
) -> FrameworkDetail:
    stmt = (
        select(Framework)
        .where(Framework.id == framework_id)
        .options(selectinload(Framework.items))
    )
    fw = (await db.execute(stmt)).scalar_one_or_none()
    if fw is None:
        raise HTTPException(404, "Framework not found")
    return FrameworkDetail.model_validate(fw)


@router.put("/frameworks/{framework_id}", response_model=FrameworkDetail)
async def update_framework(
    framework_id: str,
    body: FrameworkUpsert,
    db: AsyncSession = Depends(get_db),
) -> FrameworkDetail:
    """Full-update — replaces name, description, and the items list."""
    stmt = (
        select(Framework)
        .where(Framework.id == framework_id)
        .options(selectinload(Framework.items))
    )
    fw = (await db.execute(stmt)).scalar_one_or_none()
    if fw is None:
        raise HTTPException(404, "Framework not found")

    fw.name = body.name.strip()
    fw.description = body.description
    _replace_items(fw, body.items)
    await db.commit()
    await db.refresh(fw, attribute_names=["items"])
    return FrameworkDetail.model_validate(fw)


@router.delete("/frameworks/{framework_id}")
async def delete_framework(
    framework_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    fw = await db.get(Framework, framework_id)
    if fw is None:
        raise HTTPException(404, "Framework not found")
    await db.delete(fw)
    await db.commit()
    return Response(status_code=204)
