"""Unit tests for the Compliance validation layer.

Pure-function / pure-async tests — no DB, no real Ollama. Mocks the
ollama_caller callable.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.utils.compliance_validation import (
    NOTE_FABRICATED_PREFIX,
    NOTE_FABRICATED_SUFFIX,
    NOTE_NO_CITATION,
    RETRY_THRESHOLD,
    DocumentEvidence,
    ScorecardRow,
    apply_evidence_rule,
    build_evidence_index,
    validate_or_retry,
    verify_citations,
)


# ──────────────────────────────────────────────────────────────────────────
# 1) ScorecardRow snap-to-bucket + invalid types
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (100, 100),
        (76, 100),       # > 75 → 100
        (75, 50),        # boundary: <= 75 snaps DOWN to 50
        (75.0, 50),      # same boundary as float
        (60, 50),
        (50, 50),
        (26, 50),
        (25, 0),         # boundary: <= 25 snaps to 0
        (0, 0),
        (None, None),
    ],
)
def test_scorecard_snaps_to_bucket(raw, expected):
    row = ScorecardRow.model_validate(
        {"idx": 0, "compliance_pct": raw, "remarks": "x"}
    )
    assert row.compliance_pct == expected


def test_scorecard_rejects_string_compliance():
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(
            {"idx": 0, "compliance_pct": "high", "remarks": "x"}
        )


def test_scorecard_rejects_bool_compliance():
    """bool is a Python int subclass; explicit guard prevents True → 100."""
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(
            {"idx": 0, "compliance_pct": True, "remarks": "x"}
        )


def test_scorecard_rejects_negative_idx():
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(
            {"idx": -1, "compliance_pct": 50, "remarks": "x"}
        )


def test_scorecard_rejects_empty_remarks():
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(
            {"idx": 0, "compliance_pct": 50, "remarks": ""}
        )


def test_scorecard_rejects_overlong_remarks():
    with pytest.raises(ValidationError):
        ScorecardRow.model_validate(
            {"idx": 0, "compliance_pct": 50, "remarks": "x" * 501}
        )


def test_scorecard_accepts_500_char_remarks():
    row = ScorecardRow.model_validate(
        {"idx": 0, "compliance_pct": 50, "remarks": "x" * 500}
    )
    assert len(row.remarks) == 500


# ──────────────────────────────────────────────────────────────────────────
# 2) Evidence index extraction
# ──────────────────────────────────────────────────────────────────────────


def test_build_evidence_index_extracts_adr_ids_and_normalises_case():
    text = """\
# 1. Document Control

ADR-001 covers the cloud strategy. See also adr-014 for compute.

[Table 5 — under "Compute"]
| col |
| --- |
| x |

The pattern ADR-NNN refers to placeholder format and should be ignored.
"""
    ev = build_evidence_index(text)
    assert ev.adr_ids == {"ADR-001", "ADR-014"}
    assert "1. document control" in ev.section_headings
    assert "table 5" in ev.table_labels


def test_build_evidence_index_handles_empty_doc():
    ev = build_evidence_index("")
    assert ev.adr_ids == set()
    assert ev.section_headings == []
    assert ev.table_labels == set()


def test_build_evidence_index_extracts_multiple_headings():
    text = "# 1. Intro\n\n## 1.1 Scope\n\n### 9.3 Compute platform\n"
    ev = build_evidence_index(text)
    assert "1. intro" in ev.section_headings
    assert "1.1 scope" in ev.section_headings
    assert "9.3 compute platform" in ev.section_headings


# ──────────────────────────────────────────────────────────────────────────
# 3) Citation verification
# ──────────────────────────────────────────────────────────────────────────


def _ev(adrs=None, headings=None, tables=None) -> DocumentEvidence:
    return DocumentEvidence(
        adr_ids=set(adrs or []),
        section_headings=list(headings or []),
        table_labels=set(tables or []),
    )


def test_verify_citations_flags_fabricated_adr():
    ev = _ev(adrs={"ADR-001", "ADR-014"})
    check = verify_citations(
        "The architecture is described in ADR-001 and ADR-099.", ev
    )
    assert "ADR-099" in check.fabricated_adrs
    assert "ADR-001" not in check.fabricated_adrs
    assert check.has_any_real_citation is True


def test_verify_citations_no_fabrication_when_all_real():
    ev = _ev(adrs={"ADR-001", "ADR-021"})
    check = verify_citations("ADR-001 and adr-021 cover this.", ev)
    assert check.fabricated_adrs == set()
    assert check.cited_adrs == {"ADR-001", "ADR-021"}
    assert check.has_any_real_citation is True


def test_verify_citations_section_substring_match():
    ev = _ev(headings=["9.3 compute platform"])
    check = verify_citations("See §9.3 for details.", check_target := ev)
    assert "9.3" in check.cited_sections
    assert check.has_any_real_citation is True


def test_verify_citations_section_unmatched_does_not_set_real():
    ev = _ev(headings=["9.3 compute platform"])
    check = verify_citations("See section 12.5 for details.", ev)
    assert "12.5" in check.cited_sections
    # Section refs aren't fabrication-flagged (fuzzy domain), but they
    # also don't count as a real citation if they don't substring-match.
    assert check.has_any_real_citation is False


def test_verify_citations_table_match_and_fabrication():
    ev = _ev(tables={"table 5"})
    check = verify_citations("See Table 5 and Table 99.", ev)
    assert check.cited_tables == {"table 5", "table 99"}
    assert "table 99" in check.fabricated_tables
    assert "table 5" not in check.fabricated_tables
    assert check.has_any_real_citation is True


def test_verify_citations_empty_remarks():
    check = verify_citations("", _ev(adrs={"ADR-001"}))
    assert check.cited_adrs == set()
    assert check.has_any_real_citation is False


def test_verify_citations_ignores_adr_nnn_placeholder():
    """The literal placeholder string 'ADR-NNN' has letters, not digits,
    so the regex should skip it."""
    check = verify_citations("Use ADR-NNN as a placeholder.", _ev(adrs=set()))
    assert check.cited_adrs == set()


# ──────────────────────────────────────────────────────────────────────────
# 4) apply_evidence_rule — the load-bearing downgrade
# ──────────────────────────────────────────────────────────────────────────


def _row(idx: int = 0, pct: int | None = 100, remarks: str = "x") -> ScorecardRow:
    return ScorecardRow.model_validate(
        {"idx": idx, "compliance_pct": pct, "remarks": remarks}
    )


def test_apply_rule_downgrades_100_with_no_citations():
    row = _row(pct=100, remarks="The design covers this comprehensively.")
    check = verify_citations(row.remarks, _ev(adrs={"ADR-001"}))
    out, modified = apply_evidence_rule(row, check)
    assert modified is True
    assert out.compliance_pct == 50
    assert NOTE_NO_CITATION in out.remarks
    assert "design covers" in out.remarks  # original retained


def test_apply_rule_downgrades_100_with_only_fabricated_adr():
    row = _row(pct=100, remarks="As specified in ADR-099.")
    check = verify_citations(row.remarks, _ev(adrs={"ADR-001"}))
    out, modified = apply_evidence_rule(row, check)
    assert modified is True
    assert out.compliance_pct == 50
    assert "ADR-099" in out.remarks
    assert NOTE_FABRICATED_PREFIX in out.remarks


def test_apply_rule_passes_through_100_with_real_adr():
    row = _row(pct=100, remarks="As specified in ADR-001.")
    check = verify_citations(row.remarks, _ev(adrs={"ADR-001"}))
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct == 100
    assert out.remarks == row.remarks  # untouched


def test_apply_rule_passes_through_100_with_real_table():
    row = _row(pct=100, remarks="See Table 5 for the matrix.")
    check = verify_citations(row.remarks, _ev(tables={"table 5"}))
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct == 100


def test_apply_rule_passes_through_100_with_real_section():
    row = _row(pct=100, remarks="Per §9.3 of the SAD.")
    check = verify_citations(row.remarks, _ev(headings=["9.3 compute platform"]))
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct == 100


def test_apply_rule_does_not_touch_50():
    row = _row(pct=50, remarks="Partially covered, no specific reference.")
    check = verify_citations(row.remarks, _ev())
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct == 50


def test_apply_rule_does_not_touch_0():
    row = _row(pct=0, remarks="Not addressed.")
    check = verify_citations(row.remarks, _ev())
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct == 0


def test_apply_rule_does_not_touch_null():
    row = _row(pct=None, remarks="Not applicable.")
    check = verify_citations(row.remarks, _ev())
    out, modified = apply_evidence_rule(row, check)
    assert modified is False
    assert out.compliance_pct is None


def test_apply_rule_truncates_when_note_would_overflow():
    long = "x" * 480
    row = _row(pct=100, remarks=long)
    check = verify_citations(row.remarks, _ev())
    out, modified = apply_evidence_rule(row, check)
    assert modified is True
    assert len(out.remarks) <= 500
    # The note must still be visible at the end.
    assert NOTE_NO_CITATION in out.remarks


# ──────────────────────────────────────────────────────────────────────────
# 5) validate_or_retry — call counts + threshold
# ──────────────────────────────────────────────────────────────────────────


class _MockOllama:
    """Records calls; returns a queued list of row-dict batches."""

    def __init__(self, batches: list[list[dict]]):
        self.batches = list(batches)
        self.call_count = 0
        self.last_prompt: str | None = None

    async def __call__(self, prompt: str) -> list[dict]:
        self.call_count += 1
        self.last_prompt = prompt
        return self.batches.pop(0) if self.batches else []


@pytest.mark.asyncio
async def test_validate_or_retry_no_retry_when_clean():
    """All rows valid → ollama_caller never called."""
    raw = [
        {"idx": 0, "compliance_pct": 50, "remarks": "ok"},
        {"idx": 1, "compliance_pct": 0, "remarks": "ok"},
        {"idx": 2, "compliance_pct": 100, "remarks": "ADR-001"},
    ]
    ollama = _MockOllama([])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=3,
        framework_name="X",
        evidence=_ev(adrs={"ADR-001"}),
        ollama_caller=ollama,
    )
    assert ollama.call_count == 0
    assert out.retry_used is False
    assert len(out.rows_by_idx) == 3
    assert out.parse_failures == {}
    assert out.missing_idxs == set()


@pytest.mark.asyncio
async def test_validate_or_retry_retries_when_failure_rate_exceeds_threshold():
    """3 of 5 missing (60% > 30%) → retry once."""
    raw = [
        {"idx": 0, "compliance_pct": 50, "remarks": "ok"},
        {"idx": 1, "compliance_pct": 100, "remarks": "ADR-001"},
    ]
    second = [
        {"idx": 2, "compliance_pct": 0, "remarks": "missing"},
        {"idx": 3, "compliance_pct": 0, "remarks": "missing"},
        {"idx": 4, "compliance_pct": 50, "remarks": "recovered"},
    ]
    ollama = _MockOllama([second])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=5,
        framework_name="X",
        evidence=_ev(adrs={"ADR-001"}),
        ollama_caller=ollama,
    )
    assert ollama.call_count == 1
    assert out.retry_used is True
    assert len(out.rows_by_idx) == 5
    assert out.missing_idxs == set()


@pytest.mark.asyncio
async def test_validate_or_retry_skips_retry_below_threshold():
    """1 of 5 missing (20% < 30%) → no retry, gap stays."""
    raw = [
        {"idx": 0, "compliance_pct": 50, "remarks": "ok"},
        {"idx": 1, "compliance_pct": 50, "remarks": "ok"},
        {"idx": 2, "compliance_pct": 50, "remarks": "ok"},
        {"idx": 3, "compliance_pct": 50, "remarks": "ok"},
        # idx=4 missing
    ]
    ollama = _MockOllama([])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=5,
        framework_name="X",
        evidence=_ev(),
        ollama_caller=ollama,
    )
    assert ollama.call_count == 0
    assert out.retry_used is False
    assert out.missing_idxs == {4}


@pytest.mark.asyncio
async def test_validate_or_retry_caps_at_two_calls_total():
    """If retry also fails, never call a third time."""
    raw = []  # 0 of 5 → retry
    second_also_empty: list[dict] = []
    ollama = _MockOllama([second_also_empty])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=5,
        framework_name="X",
        evidence=_ev(),
        ollama_caller=ollama,
    )
    assert ollama.call_count == 1  # the initial pass is in `raw`, not via caller
    assert out.retry_used is True


@pytest.mark.asyncio
async def test_validate_or_retry_keeps_first_when_retry_doesnt_help():
    """Retry returns junk → keep first attempt (which had a valid row)."""
    raw = [{"idx": 0, "compliance_pct": 50, "remarks": "good"}]
    second = [{"idx": 0, "compliance_pct": "broken", "remarks": ""}]  # bad
    ollama = _MockOllama([second])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=3,
        framework_name="X",
        evidence=_ev(),
        ollama_caller=ollama,
    )
    assert 0 in out.rows_by_idx
    assert out.rows_by_idx[0].remarks == "good"
    assert out.missing_idxs == {1, 2}
    assert out.retry_used is True


@pytest.mark.asyncio
async def test_validate_or_retry_applies_evidence_rule_in_pipeline():
    """A 100 with no citation must come back downgraded to 50 + auto_modified."""
    raw = [{"idx": 0, "compliance_pct": 100, "remarks": "Looks compliant."}]
    ollama = _MockOllama([])
    out = await validate_or_retry(
        raw_rows=raw,
        expected_count=1,
        framework_name="X",
        evidence=_ev(adrs={"ADR-001"}),
        ollama_caller=ollama,
    )
    assert out.rows_by_idx[0].compliance_pct == 50
    assert 0 in out.auto_modified_idxs


def test_retry_threshold_is_exposed_as_constant():
    """Sanity — the spec requires this be a tunable module-level constant."""
    assert 0 < RETRY_THRESHOLD < 1
