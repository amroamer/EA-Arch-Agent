"""Unit tests for the evidence-enforcement rule used by the per-criterion
compliance orchestrator. Pure-function tests — no I/O, no DB, no network."""
from __future__ import annotations

import pytest

from app.utils.compliance_rules import _enforce_evidence_rule


# ── Pass-through cases ──────────────────────────────────────────────────


def test_compliant_with_real_section_citation_unchanged():
    v = {
        "compliance_pct": 100,
        "evidence": "§9.3 Compute platform",
        "remarks": "Architecture explicitly references §9.3",
    }
    assert _enforce_evidence_rule(v) == v


def test_compliant_with_adr_citation_unchanged():
    v = {
        "compliance_pct": 100,
        "evidence": "ADR-021",
        "remarks": "ADR-021 specifies active-active across two zones",
    }
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 100
    assert out["evidence"] == "ADR-021"


def test_compliant_with_table_citation_unchanged():
    v = {"compliance_pct": 100, "evidence": "Table 5", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 100


def test_compliant_with_standard_reference_unchanged():
    v = {"compliance_pct": 100, "evidence": "NCGR-EA-CAT-32", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 100


def test_partial_with_empty_evidence_unchanged():
    """Rule only fires for compliance_pct == 100. Partial passes through
    as-is even with empty evidence."""
    v = {"compliance_pct": 50, "evidence": "", "remarks": "Touched but unclear"}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 50
    assert out["remarks"] == "Touched but unclear"


def test_partial_with_none_evidence_unchanged():
    v = {"compliance_pct": 50, "evidence": "none", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 50


def test_not_compliant_with_empty_evidence_unchanged():
    v = {"compliance_pct": 0, "evidence": "", "remarks": "Explicitly contradicts"}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 0
    assert out["remarks"] == "Explicitly contradicts"


def test_na_with_none_evidence_unchanged():
    v = {"compliance_pct": None, "evidence": "none", "remarks": "Doesn't apply"}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] is None
    assert out["remarks"] == "Doesn't apply"


# ── Downgrade cases ─────────────────────────────────────────────────────


def test_compliant_with_empty_evidence_downgraded_with_remarks():
    v = {"compliance_pct": 100, "evidence": "", "remarks": "Looks great."}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 50
    assert out["evidence"] == ""  # evidence unchanged — the note is in remarks
    assert "no concrete evidence" in out["remarks"].lower()
    assert "Looks great." in out["remarks"]  # original retained


def test_compliant_with_empty_evidence_and_no_remarks():
    v = {"compliance_pct": 100, "evidence": "", "remarks": ""}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 50
    assert "no concrete evidence" in out["remarks"].lower()


def test_compliant_with_lowercase_none_downgraded():
    v = {"compliance_pct": 100, "evidence": "none", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 50


def test_compliant_with_uppercase_none_downgraded():
    v = {"compliance_pct": 100, "evidence": "NONE", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 50


def test_compliant_with_n_a_evidence_downgraded():
    """'n/a' and 'N/A' — common LLM placeholder strings."""
    for ev in ["n/a", "N/A", "Na", "NA"]:
        v = {"compliance_pct": 100, "evidence": ev, "remarks": "x"}
        assert _enforce_evidence_rule(v)["compliance_pct"] == 50, f"failed for {ev!r}"


def test_compliant_with_whitespace_evidence_downgraded():
    v = {"compliance_pct": 100, "evidence": "   \n\t  ", "remarks": "x"}
    assert _enforce_evidence_rule(v)["compliance_pct"] == 50


def test_compliant_with_punctuation_only_evidence_downgraded():
    """Defensive — model sometimes emits placeholder dashes."""
    for ev in ["—", "-", "–", "...", ".", ","]:
        v = {"compliance_pct": 100, "evidence": ev, "remarks": "x"}
        assert _enforce_evidence_rule(v)["compliance_pct"] == 50, f"failed for {ev!r}"


def test_compliant_with_none_python_value_downgraded():
    """If the model returns a JSON null for evidence (Python None)."""
    v = {"compliance_pct": 100, "evidence": None, "remarks": "x"}
    out = _enforce_evidence_rule(v)
    assert out["compliance_pct"] == 50


# ── Idempotency ────────────────────────────────────────────────────────


def test_idempotent():
    v = {"compliance_pct": 100, "evidence": "", "remarks": "Original."}
    once = _enforce_evidence_rule(v)
    twice = _enforce_evidence_rule(once)
    assert once == twice
    assert once["compliance_pct"] == 50
    # Note appears only once, not twice
    assert once["remarks"].count("Server downgrade") == 1


def test_idempotent_after_third_pass():
    v = {"compliance_pct": 100, "evidence": "none", "remarks": ""}
    a = _enforce_evidence_rule(v)
    b = _enforce_evidence_rule(a)
    c = _enforce_evidence_rule(b)
    assert a == b == c


# ── Purity ─────────────────────────────────────────────────────────────


def test_does_not_mutate_input():
    v = {"compliance_pct": 100, "evidence": "", "remarks": "x"}
    snapshot = dict(v)
    _ = _enforce_evidence_rule(v)
    assert v == snapshot, "_enforce_evidence_rule mutated its input"


# ── Sanity on float pct (snapped non-categorical from upstream) ────────


def test_compliant_as_float_treated_same_as_int():
    """If upstream snapped to 100.0, rule still applies."""
    v = {"compliance_pct": 100.0, "evidence": "", "remarks": "x"}
    out = _enforce_evidence_rule(v)
    # Note: 100.0 != 100 in `is` but == in equality. Rule uses `!=` check
    # so this should still trip. Document the behaviour explicitly.
    assert out["compliance_pct"] == 50
