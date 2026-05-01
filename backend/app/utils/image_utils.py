"""Image validation, resizing, and base64 encoding.

The longest edge is capped at `IMAGE_RESIZE_MAX_EDGE` (default 1568 px) —
this is Gemma 4 vision's preferred tile ceiling. Resizing here happens
server-side as a defense-in-depth measure: the frontend also resizes
client-side before upload, but never trust the client.
"""
from __future__ import annotations

import base64
import hashlib
import io
import logging

from PIL import Image, UnidentifiedImageError

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"PNG", "JPEG"}
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/jpg"}


class ImageValidationError(ValueError):
    """User-supplied image failed validation."""


class ProcessedImage:
    """Result of validate_and_resize — bundles everything callers need."""

    def __init__(
        self,
        *,
        resized_bytes: bytes,
        b64: str,
        sha256: str,
        content_type: str,
        width: int,
        height: int,
    ) -> None:
        self.resized_bytes = resized_bytes
        self.b64 = b64
        self.sha256 = sha256
        self.content_type = content_type
        self.width = width
        self.height = height


def validate_and_resize(
    raw_bytes: bytes,
    *,
    content_type: str | None = None,
    max_edge: int | None = None,
    max_bytes: int | None = None,
) -> ProcessedImage:
    """Validate an uploaded image and return a ProcessedImage.

    Steps:
        1. Reject if oversize (raw bytes > max_bytes).
        2. Reject if MIME doesn't look like PNG/JPEG.
        3. Open with Pillow; reject on UnidentifiedImageError.
        4. Reject formats outside ALLOWED_FORMATS.
        5. If longest edge > max_edge, resample down (LANCZOS).
        6. Re-encode to JPEG q90 (or keep PNG if originally PNG and small).
        7. Return resized bytes + base64 + sha256 (of ORIGINAL bytes —
           used as dedup key) + final content_type + post-resize dims.
    """
    max_bytes = max_bytes or settings.max_upload_bytes
    max_edge = max_edge or settings.image_resize_max_edge

    if len(raw_bytes) > max_bytes:
        raise ImageValidationError(
            f"Image exceeds max upload size "
            f"({len(raw_bytes):,} > {max_bytes:,} bytes)"
        )
    if content_type and content_type.lower() not in ALLOWED_MIMES:
        raise ImageValidationError(f"Unsupported MIME type: {content_type}")

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()  # force decode now so errors raise here, not later
    except UnidentifiedImageError as exc:
        raise ImageValidationError(f"Could not identify image: {exc}")
    except Exception as exc:  # Pillow throws various errors for bad files
        raise ImageValidationError(f"Image decode failed: {exc}")

    if img.format not in ALLOWED_FORMATS:
        raise ImageValidationError(f"Unsupported image format: {img.format}")

    original_format = img.format

    # Convert palette / RGBA / CMYK to RGB before re-encoding to JPEG.
    if img.mode not in {"RGB", "L"}:
        img = img.convert("RGB")

    # Resize if needed. Preserve aspect ratio.
    longest = max(img.size)
    if longest > max_edge:
        ratio = max_edge / longest
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        logger.info(
            "image_utils: resizing %dx%d -> %dx%d", *img.size, *new_size
        )
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Re-encode. JPEG q90 hits a good size/quality balance for screenshots.
    out = io.BytesIO()
    if original_format == "PNG" and longest <= max_edge:
        img.save(out, format="PNG", optimize=True)
        out_content_type = "image/png"
    else:
        img.save(out, format="JPEG", quality=90, optimize=True)
        out_content_type = "image/jpeg"
    resized = out.getvalue()

    sha = hashlib.sha256(raw_bytes).hexdigest()
    b64 = base64.b64encode(resized).decode("ascii")
    return ProcessedImage(
        resized_bytes=resized,
        b64=b64,
        sha256=sha,
        content_type=out_content_type,
        width=img.size[0],
        height=img.size[1],
    )
