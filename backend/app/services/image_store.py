"""Idempotent persistence for uploaded images.

Images are content-addressed by sha256. Multiple Sessions that reference
the same image only store the bytes once.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Image
from app.utils.image_utils import ProcessedImage


async def upsert_image(db: AsyncSession, processed: ProcessedImage) -> None:
    """Insert the image row if its sha256 isn't already stored.

    Cheaper than INSERT ... ON CONFLICT for our scale; the existence check
    avoids a useless write of ~200 KB on dedup hits.
    """
    existing = await db.execute(
        select(Image.sha256).where(Image.sha256 == processed.sha256)
    )
    if existing.scalar_one_or_none() is not None:
        return  # already stored

    db.add(
        Image(
            sha256=processed.sha256,
            content_type=processed.content_type,
            bytes=processed.resized_bytes,
            byte_size=len(processed.resized_bytes),
            width=processed.width,
            height=processed.height,
        )
    )
    # Caller is responsible for the surrounding commit.
