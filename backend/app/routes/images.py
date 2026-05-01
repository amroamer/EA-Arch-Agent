"""GET /images/{sha256} — serve a stored image.

Used by the SessionDetail page to render the diagrams that were uploaded
for past Analyze/Compare runs. Cached aggressively — content-addressed
URLs are immutable.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import Image

router = APIRouter()

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


@router.get("/images/{sha256}")
async def get_image(
    sha256: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not _SHA256_RE.match(sha256):
        raise HTTPException(400, "Invalid image hash")
    row = await db.get(Image, sha256.lower())
    if row is None:
        raise HTTPException(404, "Image not found")
    return Response(
        content=row.bytes,
        media_type=row.content_type,
        headers={
            # Content-addressable, so cache forever.
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Length": str(row.byte_size),
        },
    )
