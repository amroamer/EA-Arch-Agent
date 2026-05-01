"""Extract embedded images and structured text from a .docx upload.

A .docx is a ZIP of XML; the model needs vision input plus any prose
context the doc provides. We extract:

- All embedded raster images (typically `word/media/imageN.png|jpeg`).
- The body in DOCUMENT ORDER as Markdown-ish text:
    - Heading paragraphs ("Heading 1".."Heading 6") become `#`..`######`
      lines.
    - Body paragraphs are emitted as plain text.
    - Tables are numbered, captioned with the previous heading, and
      rendered as Markdown pipe tables.

Document order matters: the model needs to associate a §9.3 heading
with the table that follows it, and an ADR table with the section it
appears under. The original implementation flattened paragraphs and
tables separately, scrambling the narrative.

The /analyze route uses the FIRST extracted image as the primary
visual (passed through the normal validate_and_resize pipeline) and
prepends the extracted text to the user prompt as additional context.
"""
from __future__ import annotations

import io
import logging
import re

from docx import Document
from docx.opc.constants import CONTENT_TYPE as CT
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)


DOCX_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocxExtractionError(ValueError):
    """The uploaded .docx couldn't be parsed."""


class ExtractedDocx:
    """Result of extract_docx: image bytes + structured text + metadata."""

    def __init__(
        self,
        *,
        images: list[tuple[bytes, str]],  # (bytes, content_type)
        text: str,
    ) -> None:
        self.images = images
        self.text = text


# python-docx exposes image parts via `Document.part.related_parts`. We
# accept any image content type Pillow can later open; PNG/JPEG cover
# the overwhelming majority of architecture screenshots.
_IMAGE_CONTENT_TYPES = {
    CT.PNG,            # 'image/png'
    CT.JPEG,           # 'image/jpeg'
    "image/jpg",       # some clients normalize to this
}

# Recognise heading styles like "Heading 1", "Heading 2", "heading 3".
_HEADING_RE = re.compile(r"^heading\s+(\d+)$", re.IGNORECASE)


def _heading_level(p: Paragraph) -> int | None:
    """Return 1..6 if the paragraph uses a 'Heading N' style, else None."""
    try:
        name = (p.style.name or "").strip()
    except Exception:  # noqa: BLE001 — defensive against odd style refs
        return None
    m = _HEADING_RE.match(name)
    if not m:
        return None
    level = int(m.group(1))
    return level if 1 <= level <= 6 else None


def _format_table(t: Table, *, table_num: int, caption_hint: str | None) -> str:
    """Render a Word table as a Markdown pipe table, prefixed with a label."""
    rows = list(t.rows)
    if not rows:
        return ""

    # Cell texts. Use ' '.join over all paragraphs in the cell so multi-line
    # cells become single-line table cells (Markdown tables don't support
    # embedded newlines without escaping).
    def cell_text(cell) -> str:
        text = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
        return text.replace("|", "\\|").strip() or " "

    matrix = [[cell_text(c) for c in row.cells] for row in rows]
    if not any(any(c.strip() for c in row) for row in matrix):
        return ""  # skip wholly-empty tables

    n_cols = max(len(row) for row in matrix)
    matrix = [row + [" "] * (n_cols - len(row)) for row in matrix]

    # Treat first row as header.
    header = matrix[0]
    body = matrix[1:]

    label_bits = [f"Table {table_num}"]
    if caption_hint:
        label_bits.append(f"under \"{caption_hint}\"")
    label = f"[{' — '.join(label_bits)}]"

    lines = [label]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def extract_docx(raw_bytes: bytes) -> ExtractedDocx:
    """Parse a .docx and return its embedded images and structured text.

    Raises DocxExtractionError on parse failure.
    """
    try:
        doc = Document(io.BytesIO(raw_bytes))
    except Exception as exc:  # noqa: BLE001 — python-docx wraps many failure modes
        raise DocxExtractionError(f"Could not parse .docx: {exc}") from exc

    # ── Images: walk all related parts, keep raster image content types.
    images: list[tuple[bytes, str]] = []
    for rel in doc.part.related_parts.values():
        ct = (getattr(rel, "content_type", "") or "").lower()
        if ct in _IMAGE_CONTENT_TYPES:
            blob = getattr(rel, "blob", None)
            if blob:
                images.append((blob, ct))

    # ── Body in document order: paragraphs and tables interleaved.
    out_lines: list[str] = []
    table_num = 0
    last_heading: str | None = None

    body = doc.element.body
    p_tag = qn("w:p")
    tbl_tag = qn("w:tbl")

    for child in body.iterchildren():
        if child.tag == p_tag:
            p = Paragraph(child, doc)
            text = p.text.strip()
            if not text:
                continue
            level = _heading_level(p)
            if level is not None:
                out_lines.append(f"{'#' * level} {text}")
                last_heading = text
            else:
                out_lines.append(text)
        elif child.tag == tbl_tag:
            table_num += 1
            t = Table(child, doc)
            rendered = _format_table(t, table_num=table_num, caption_hint=last_heading)
            if rendered:
                out_lines.append("")  # blank line before table
                out_lines.append(rendered)
                out_lines.append("")  # blank line after table
        # else: silently skip section properties, etc.

    text = "\n".join(out_lines).strip()

    logger.info(
        "docx_utils: extracted %d images + %d tables + %d text chars",
        len(images),
        table_num,
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
