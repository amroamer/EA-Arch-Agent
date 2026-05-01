"""Extract embedded images and plain text from a .docx upload.

A .docx is a ZIP archive of XML; the model needs vision input plus any
prose context the doc provides about the architecture. We pull both:
- All embedded raster images (typically `word/media/imageN.png|jpeg`).
- Concatenated paragraph + table-cell text.

The /analyze route uses the FIRST extracted image as the primary visual
(passed through the normal validate_and_resize pipeline) and prepends the
extracted text to the user prompt for additional context.
"""
from __future__ import annotations

import io
import logging

from docx import Document
from docx.opc.constants import CONTENT_TYPE as CT

logger = logging.getLogger(__name__)


DOCX_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocxExtractionError(ValueError):
    """The uploaded .docx couldn't be parsed."""


class ExtractedDocx:
    """Result of extract_docx: images bytes + text + a name hint."""

    def __init__(
        self,
        *,
        images: list[tuple[bytes, str]],  # (bytes, content_type)
        text: str,
    ) -> None:
        self.images = images
        self.text = text


# python-docx exposes image parts via `Document.part.related_parts`. We
# accept any image content type Pillow can later open; PNG/JPEG cover the
# overwhelming majority of architecture screenshots embedded in docs.
_IMAGE_CONTENT_TYPES = {
    CT.PNG,            # 'image/png'
    CT.JPEG,           # 'image/jpeg'
    "image/jpg",       # some clients normalize to this
}


def extract_docx(raw_bytes: bytes) -> ExtractedDocx:
    """Parse a .docx and return its embedded images and full text.

    Raises DocxExtractionError on parse failure.
    """
    try:
        doc = Document(io.BytesIO(raw_bytes))
    except Exception as exc:  # noqa: BLE001 — python-docx wraps many failure modes
        raise DocxExtractionError(f"Could not parse .docx: {exc}") from exc

    # ── Images: walk all related parts, keep raster image content types.
    images: list[tuple[bytes, str]] = []
    for rel_id, rel in doc.part.related_parts.items():
        ct = getattr(rel, "content_type", "") or ""
        if ct.lower() in _IMAGE_CONTENT_TYPES:
            blob = getattr(rel, "blob", None)
            if blob:
                images.append((blob, ct.lower()))
        else:
            # Non-image relationship — skip silently.
            del rel_id  # appease linters about unused var

    # ── Text: paragraphs + tables. Preserve some structure.
    parts: list[str] = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells]
            row_text = " | ".join(c for c in row_cells if c)
            if row_text:
                parts.append(row_text)

    text = "\n".join(parts).strip()
    logger.info(
        "docx_utils: extracted %d images + %d text chars",
        len(images),
        len(text),
    )
    return ExtractedDocx(images=images, text=text)


def is_docx(content_type: str | None, filename: str | None) -> bool:
    """Cheap sniff: trust either MIME or extension. Browsers vary."""
    if content_type and content_type.lower() in DOCX_MIMES:
        return True
    if filename and filename.lower().endswith(".docx"):
        return True
    return False
