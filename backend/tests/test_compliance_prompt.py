"""Tests for the v2 Compliance system prompt — placeholder integrity,
prompt assembly, and the override-validation guard.

These tests intentionally do NOT call Ollama. They verify the prompt
that would be sent to Ollama is the new v2 prompt and that user-saved
overrides cannot drop required placeholders without server rejection.
"""
from __future__ import annotations

import pytest

from app.prompts.analyze_compliance import build_compliance_prompt
from app.prompts.defaults import (
    ANALYZE_COMPLIANCE_DEFAULT,
    COMPLIANCE_DEFAULT_VERSION,
    DEFAULTS,
)
from app.routes.prompts import _placeholders_in, _validate_template

REQUIRED = {"framework_name", "criteria_block", "max_idx"}


# ── Default-template integrity ─────────────────────────────────────────


def test_compliance_default_contains_required_placeholders():
    """The v2 default still uses exactly the placeholders the orchestrator
    injects — if any one were missing, the runtime .format() call would
    KeyError on every Compliance run."""
    placeholders = _placeholders_in(ANALYZE_COMPLIANCE_DEFAULT)
    missing = REQUIRED - placeholders
    assert not missing, (
        f"v2 default is missing required placeholders: {missing}. "
        "Check the {framework_name} / {criteria_block} / {max_idx} tokens."
    )


def test_compliance_catalogue_placeholders_match_default():
    """The DEFAULTS catalogue's declared placeholders must match the
    set actually used by the template — drift here breaks the
    placeholder-validation guard's promise."""
    spec = DEFAULTS["analyze_compliance"]
    assert set(spec["placeholders"]) == REQUIRED


def test_compliance_default_is_v2():
    """The version constant ratchets when the default text changes
    materially. v2 ships with this PR."""
    assert COMPLIANCE_DEFAULT_VERSION == "v2"


def test_v2_contains_role_anchor():
    """Hardcoded sentinel — the v2 prompt opens with the consultant role
    line. If this string disappears, someone has silently rewritten the
    prompt without updating the version constant."""
    assert (
        "You are a senior enterprise architect reviewer working on behalf "
        "of a KPMG Saudi Arabia consultant." in ANALYZE_COMPLIANCE_DEFAULT
    )


def test_v2_contains_anti_hallucination_rules():
    """The 5-rule hard-rules section is the load-bearing change in v2."""
    assert "Hard rules — do not violate" in ANALYZE_COMPLIANCE_DEFAULT
    assert "Never invent ADR identifiers" in ANALYZE_COMPLIANCE_DEFAULT
    assert "no specific reference found" in ANALYZE_COMPLIANCE_DEFAULT


# ── Prompt assembly (the integration-style test) ───────────────────────


def test_build_compliance_prompt_renders_role_line_with_default():
    """Hitting build_compliance_prompt with the live default produces a
    prompt whose first sentence is the v2 role anchor — this is the prompt
    that the /analyze endpoint will hand to stream_chat()."""
    items = [
        {"criteria": "Q1-S-INF-1.1: Is the design …", "weight_planned": 25.0},
        {"criteria": "Q2-S-INF-1.2: …", "weight_planned": 20.0},
    ]
    rendered = build_compliance_prompt(framework_name="Infrastructure", items=items)

    # Role line is at the very top — first 200 chars guard against
    # someone accidentally appending content before it.
    assert rendered.startswith(
        "You are a senior enterprise architect reviewer working on behalf "
        "of a KPMG Saudi Arabia consultant."
    )

    # Placeholders are populated, not literal.
    assert "{framework_name}" not in rendered
    assert "{criteria_block}" not in rendered
    assert "{max_idx}" not in rendered

    # Framework name made it in; the criteria block did too.
    assert "Infrastructure" in rendered
    assert "Q1-S-INF-1.1" in rendered
    assert "Q2-S-INF-1.2" in rendered


def test_build_compliance_prompt_uses_explicit_template_when_provided():
    """When the orchestrator passes an override template, the builder
    must use that, not the module's default."""
    custom = (
        "CUSTOM_OVERRIDE_FOR_TESTS\n"
        "framework={framework_name}\n"
        "criteria={criteria_block}\n"
        "last={max_idx}\n"
    )
    rendered = build_compliance_prompt(
        framework_name="Cloud",
        items=[{"criteria": "Q1: x", "weight_planned": 100}],
        template=custom,
    )
    assert rendered.startswith("CUSTOM_OVERRIDE_FOR_TESTS")
    assert "framework=Cloud" in rendered
    assert "last=0" in rendered  # max_idx for a 1-item framework


def test_v2_jsonish_braces_are_doubled_so_format_doesnt_crash():
    """The literal `{"idx": ...}` example in the SCORECARD section must
    appear as `{{...}}` in source so str.format() doesn't try to bind
    `idx`. Regression guard: render with no items and confirm no
    KeyError + the example survived."""
    rendered = build_compliance_prompt(framework_name="X", items=[])
    # The literal example was preserved (single braces in the OUTPUT).
    assert '{"idx": 0' in rendered
    assert '{"idx": 1' in rendered


# ── Placeholder-validation guard (the override safety net) ─────────────


def test_validate_rejects_override_missing_framework_name():
    with pytest.raises(Exception) as exc_info:
        _validate_template(
            "analyze_compliance",
            "this template has {criteria_block} and {max_idx} but not the first one",
        )
    assert "framework_name" in str(exc_info.value).lower() or "missing" in str(
        exc_info.value
    ).lower()


def test_validate_rejects_override_missing_criteria_block():
    with pytest.raises(Exception) as exc_info:
        _validate_template(
            "analyze_compliance",
            "{framework_name} and {max_idx} only",
        )
    assert "criteria_block" in str(exc_info.value).lower() or "missing" in str(
        exc_info.value
    ).lower()


def test_validate_rejects_override_missing_max_idx():
    with pytest.raises(Exception) as exc_info:
        _validate_template(
            "analyze_compliance",
            "{framework_name} and {criteria_block} only",
        )
    assert "max_idx" in str(exc_info.value).lower() or "missing" in str(
        exc_info.value
    ).lower()


def test_validate_accepts_override_with_all_three_placeholders():
    """Sanity check that the validator isn't broken in the other direction."""
    # Should NOT raise.
    _validate_template(
        "analyze_compliance",
        "Custom: {framework_name} / {criteria_block} / {max_idx} — done.",
    )


def test_validate_rejects_unknown_key():
    with pytest.raises(Exception):
        _validate_template("not_a_real_prompt", "some template")
