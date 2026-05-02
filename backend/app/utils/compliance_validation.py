"""Server-side validation layer for Compliance scorecard rows.

Three layers of defence between Ollama's output and the consultant:

1. **Strict Pydantic schema** — coerce/snap compliance_pct, enforce
   remarks length, reject non-numeric verdicts, etc.
2. **Citation verification** — extract ADR / section / table references
   from the model's `remarks` and check each one against an index
   pre-built from the source document. Fabricated citations are flagged.
3. **Evidence-enforcement rule** — a `100` (Compliant) verdict that
   either (a) carries no real citation, or (b) cites only fabricated
   identifiers, is automatically downgraded to `50` and the reason is
   appended to remarks.

Plus a `validate_or_retry` helper for the orchestrator: collect raw rows
across the framework's stream; if too many failed validation OR the model
skipped rows entirely, build a focused retry prompt and call Ollama once
more. Caps total Ollama calls per framework at 2 (initial + at most one
retry).

This module is standalone — it does NOT import from analyze.py or any
route handler — so the per-criterion path can call the same functions.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# ── Tuning knobs ─────────────────────────────────────────────────────────


# If (parse failures + missing rows) / expected exceeds this, retry once.
RETRY_THRESHOLD: float = 0.30

# Server notes appended to remarks when the validator modifies a row.
# Stable strings so tests can assert against them.
NOTE_NO_CITATION = (
    "[auto-downgraded: Compliant requires a verifiable citation]"
)
NOTE_FABRICATED_PREFIX = "[auto-downgraded: cited "
NOTE_FABRICATED_SUFFIX = " not found in document]"
NOTE_BACKFILLED = "[server: model did not return a verdict for this criterion]"


# ── Pydantic schemas ─────────────────────────────────────────────────────


class ScorecardRow(BaseModel):
    """One scored criterion as it leaves the validator. compliance_pct is
    snapped to {0, 50, 100, None} so downstream code can rely on the
    categorical contract."""

    idx: int = Field(ge=0)
    compliance_pct: Optional[Literal[0, 50, 100]] = None
    remarks: str = Field(min_length=1, max_length=500)

    @field_validator("compliance_pct", mode="before")
    @classmethod
    def snap_to_bucket(cls, v):
        """Coerce numeric inputs to the nearest bucket. None passes through.
        Non-numeric inputs raise ValidationError."""
        if v is None:
            return None
        if isinstance(v, bool):  # bool is a subclass of int — exclude explicitly
            raise ValueError("compliance_pct must be numeric or null")
        if not isinstance(v, (int, float)):
            raise ValueError(
                f"compliance_pct must be numeric or null, got {type(v).__name__}"
            )
        f = float(v)
        if f <= 25:
            return 0
        if f <= 75:
            return 50
        return 100


# ── Document evidence index ──────────────────────────────────────────────


@dataclass
class DocumentEvidence:
    """Pre-extracted citable artefacts from the source document."""

    adr_ids: set[str] = field(default_factory=set)
    section_headings: list[str] = field(default_factory=list)
    table_labels: set[str] = field(default_factory=set)


# Document side — applied to the structured docx output.
_ADR_DOC_RE = re.compile(r"\bADR-\d{1,4}\b", re.IGNORECASE)
_HEADING_DOC_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_TABLE_DOC_RE = re.compile(r"\[Table\s+(\d+)\b", re.IGNORECASE)

# Remarks side — applied to whatever the model wrote in remarks.
_ADR_RMK_RE = re.compile(r"\bADR-\d{1,4}\b", re.IGNORECASE)
_TABLE_RMK_RE = re.compile(r"\bTable\s+(\d+)\b", re.IGNORECASE)
_SECTION_RMK_RE = re.compile(
    r"(?:§|section|sec\.?)\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


def build_evidence_index(structured_doc_text: str) -> DocumentEvidence:
    """Walk the structured docx output (Markdown headings + labelled tables
    + free prose) and extract every citable artefact. Lowercased / uppercased
    to match-canonical so case differences in remarks don't fabricate
    false positives."""
    if not structured_doc_text:
        return DocumentEvidence()

    adrs = {m.group(0).upper() for m in _ADR_DOC_RE.finditer(structured_doc_text)}
    headings = [
        h.strip().lower() for h in _HEADING_DOC_RE.findall(structured_doc_text)
    ]
    tables = {
        f"table {m.group(1)}" for m in _TABLE_DOC_RE.finditer(structured_doc_text)
    }
    return DocumentEvidence(
        adr_ids=adrs,
        section_headings=headings,
        table_labels=tables,
    )


# ── Citation verification ────────────────────────────────────────────────


@dataclass
class CitationCheck:
    """Result of comparing remark-cited references against the document."""

    cited_adrs: set[str] = field(default_factory=set)
    cited_tables: set[str] = field(default_factory=set)
    cited_sections: list[str] = field(default_factory=list)

    fabricated_adrs: set[str] = field(default_factory=set)
    fabricated_tables: set[str] = field(default_factory=set)
    # We don't attempt fabricated_sections — section refs are fuzzy
    # (substring-match against headings) so a "cited but unmatched"
    # section is more often a vague reference than a hallucination.

    has_any_real_citation: bool = False


def _section_in_doc(section_ref: str, headings: list[str]) -> bool:
    """A section reference (e.g. '9.3') matches a heading if the ref is a
    substring of any heading after normalisation."""
    needle = section_ref.strip().lower()
    if not needle:
        return False
    return any(needle in h for h in headings)


def verify_citations(remarks: str, evidence: DocumentEvidence) -> CitationCheck:
    """Extract ADR / section / table refs from `remarks` and compare to
    the document's evidence index."""
    if not remarks:
        return CitationCheck()

    cited_adrs = {m.group(0).upper() for m in _ADR_RMK_RE.finditer(remarks)}
    cited_tables = {
        f"table {m.group(1)}" for m in _TABLE_RMK_RE.finditer(remarks)
    }
    cited_sections = [m.group(1) for m in _SECTION_RMK_RE.finditer(remarks)]

    fabricated_adrs = cited_adrs - evidence.adr_ids
    fabricated_tables = cited_tables - evidence.table_labels

    real_adrs = cited_adrs - fabricated_adrs
    real_tables = cited_tables - fabricated_tables
    real_sections = [
        s for s in cited_sections if _section_in_doc(s, evidence.section_headings)
    ]

    return CitationCheck(
        cited_adrs=cited_adrs,
        cited_tables=cited_tables,
        cited_sections=cited_sections,
        fabricated_adrs=fabricated_adrs,
        fabricated_tables=fabricated_tables,
        has_any_real_citation=bool(real_adrs or real_tables or real_sections),
    )


# ── The downgrade rule ───────────────────────────────────────────────────


def apply_evidence_rule(
    row: ScorecardRow, check: CitationCheck
) -> tuple[ScorecardRow, bool]:
    """Server-side enforcement of the Compliant-requires-evidence rule.

    Returns (row, was_modified). `was_modified` is True when the row's
    compliance_pct was downgraded — used by the orchestrator to set the
    streaming `auto_modified` flag.

    50 / 0 / null pass through unchanged. Only `100` is checked.
    """
    if row.compliance_pct != 100:
        return row, False

    note: str | None = None

    if check.fabricated_adrs:
        # Naming the fabricated IDs in the note is the more useful failure
        # mode (consultant can grep for them). Sort for deterministic output.
        ids = ", ".join(sorted(check.fabricated_adrs))
        note = f"{NOTE_FABRICATED_PREFIX}{ids}{NOTE_FABRICATED_SUFFIX}"
    elif not check.has_any_real_citation:
        note = NOTE_NO_CITATION

    if note is None:
        return row, False

    new_remarks = (
        f"{row.remarks} {note}"
        if note not in (row.remarks or "")
        else row.remarks
    )
    # Truncate so we don't blow past Pydantic's 500-char limit even after
    # appending the note. Truncate from the front of the original remarks
    # to keep the auto-note visible.
    if len(new_remarks) > 500:
        keep = 500 - len(note) - 4  # "… " prefix
        new_remarks = f"…{(row.remarks or '')[-keep:]} {note}"

    return (
        ScorecardRow(
            idx=row.idx,
            compliance_pct=50,
            remarks=new_remarks,
        ),
        True,
    )


# ── Validate-or-retry orchestration helper ───────────────────────────────


@dataclass
class _RowOutcome:
    """Internal aggregate of how one row fared through validation."""

    idx: int
    row: ScorecardRow | None         # None if validation failed
    auto_modified: bool = False
    error: str | None = None         # populated when row is None


def _coerce_row(raw: dict) -> _RowOutcome:
    """Pydantic-validate one raw row. On failure, capture the error string."""
    try:
        validated = ScorecardRow.model_validate(raw)
    except ValidationError as e:
        return _RowOutcome(
            idx=int(raw.get("idx", -1) if isinstance(raw.get("idx"), (int, float)) else -1),
            row=None,
            error=_format_validation_error(e),
        )
    return _RowOutcome(idx=validated.idx, row=validated)


def _format_validation_error(e: ValidationError) -> str:
    """Compress a Pydantic ValidationError into one short line per issue
    (joined by '; ') for embedding in the retry prompt."""
    parts: list[str] = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "?"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


@dataclass
class ValidationOutcome:
    """Bundle returned to the orchestrator after the post-stream tally."""

    rows_by_idx: dict[int, ScorecardRow]
    auto_modified_idxs: set[int]
    parse_failures: dict[int, str]   # idx → error string
    missing_idxs: set[int]
    retry_used: bool


async def validate_or_retry(
    *,
    raw_rows: list[dict],
    expected_count: int,
    framework_name: str,
    evidence: DocumentEvidence,
    ollama_caller: Callable[[str], Awaitable[list[dict]]],
    retry_prompt_builder: Callable[[list[str]], str] | None = None,
) -> ValidationOutcome:
    """Validate every raw row, decide whether to retry, and return a
    consolidated outcome. The orchestrator emits the SSE events; this
    helper is purely state.

    `ollama_caller` takes a retry prompt and returns the parsed list of
    raw row dicts (the caller of this module is responsible for assembling
    a new full prompt and parsing the response — keeps this module
    decoupled from stream_chat).

    `retry_prompt_builder` is optional; if None, a sensible default is used.
    """
    if retry_prompt_builder is None:
        retry_prompt_builder = _default_retry_prompt_builder

    rows_by_idx, auto_idxs, parse_failures = _validate_pass(raw_rows, evidence)
    missing = _compute_missing(rows_by_idx, parse_failures, expected_count)

    failure_rate = (len(parse_failures) + len(missing)) / max(expected_count, 1)
    retry_used = False

    if failure_rate >= RETRY_THRESHOLD:
        errors = _retry_error_summary(parse_failures, missing)
        retry_prompt = retry_prompt_builder(errors)
        try:
            second_raw = await ollama_caller(retry_prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "compliance_retry_failed",
                extra={
                    "framework": framework_name,
                    "exception": str(exc),
                },
            )
            second_raw = []

        retry_used = True

        if second_raw:
            r2_rows, r2_auto, r2_failures = _validate_pass(second_raw, evidence)
            r2_missing = _compute_missing(r2_rows, r2_failures, expected_count)
            r2_failure_count = len(r2_failures) + len(r2_missing)
            first_failure_count = len(parse_failures) + len(missing)

            # Use the second result only if it reduces the failure count.
            if r2_failure_count < first_failure_count:
                # Merge retry results: any idx the retry recovered replaces
                # whatever we had for that idx; everything else stays.
                for idx, row in r2_rows.items():
                    rows_by_idx[idx] = row
                    parse_failures.pop(idx, None)
                auto_idxs.update(r2_auto)
                # Recompute missing now that we may have filled some gaps.
                missing = _compute_missing(
                    rows_by_idx, parse_failures, expected_count
                )

    return ValidationOutcome(
        rows_by_idx=rows_by_idx,
        auto_modified_idxs=auto_idxs,
        parse_failures=parse_failures,
        missing_idxs=missing,
        retry_used=retry_used,
    )


def _validate_pass(
    raw_rows: list[dict], evidence: DocumentEvidence
) -> tuple[dict[int, ScorecardRow], set[int], dict[int, str]]:
    """One full validation pass: coerce + citation-check every raw row.
    Returns (rows_by_idx, auto_modified_idxs, parse_failures_by_idx)."""
    rows_by_idx: dict[int, ScorecardRow] = {}
    auto_idxs: set[int] = set()
    parse_failures: dict[int, str] = {}

    for raw in raw_rows:
        outcome = _coerce_row(raw)
        if outcome.row is None:
            parse_failures[outcome.idx] = outcome.error or "validation failed"
            continue
        check = verify_citations(outcome.row.remarks, evidence)
        modified, was_modified = apply_evidence_rule(outcome.row, check)
        rows_by_idx[modified.idx] = modified
        if was_modified:
            auto_idxs.add(modified.idx)

    return rows_by_idx, auto_idxs, parse_failures


def _compute_missing(
    rows_by_idx: dict[int, ScorecardRow],
    parse_failures: dict[int, str],
    expected_count: int,
) -> set[int]:
    """Indices in 0..expected_count-1 that have neither a valid row nor a
    parse-failure record."""
    seen = set(rows_by_idx) | set(parse_failures)
    return {i for i in range(expected_count) if i not in seen}


def _retry_error_summary(
    parse_failures: dict[int, str], missing: set[int]
) -> list[str]:
    lines: list[str] = []
    for idx in sorted(parse_failures):
        lines.append(f"Row idx={idx}: {parse_failures[idx]}")
    if missing:
        lines.append(
            "Missing rows: " + ", ".join(str(i) for i in sorted(missing))
        )
    return lines


def _default_retry_prompt_builder(errors: list[str]) -> str:
    """A short retry prompt — under 500 tokens to keep the 7B happy."""
    bullet_block = "\n".join(f"- {e}" for e in errors[:20])
    return (
        "The previous SCORECARD response had validation errors:\n"
        f"{bullet_block}\n\n"
        "Reproduce the SCORECARD section ONLY, fixing these errors. "
        "Use the same NARRATIVE you produced before (do not re-emit it). "
        "Each row must be valid JSON with idx (int), compliance_pct "
        "(100, 50, 0, or null), and remarks (1-500 chars). "
        "Only cite ADRs, sections, or tables that actually appear in the "
        "provided document — do not invent identifiers."
    )


__all__ = [
    "RETRY_THRESHOLD",
    "NOTE_NO_CITATION",
    "NOTE_FABRICATED_PREFIX",
    "NOTE_FABRICATED_SUFFIX",
    "NOTE_BACKFILLED",
    "ScorecardRow",
    "DocumentEvidence",
    "CitationCheck",
    "ValidationOutcome",
    "build_evidence_index",
    "verify_citations",
    "apply_evidence_rule",
    "validate_or_retry",
]
