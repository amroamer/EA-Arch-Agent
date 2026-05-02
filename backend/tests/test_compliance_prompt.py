"""Tests for the v2 Compliance system prompt — placeholder integrity,
prompt assembly, and the override-validation guard.

These tests intentionally do NOT call Ollama. They verify the prompt
that would be sent to Ollama is the new v2 prompt and that user-saved
overrides cannot drop required placeholders without server rejection.
"""
from __future__ import annotations

import pytest

from app.prompts.analyze_compliance import (
    build_compliance_prompt,
    build_per_criterion_prompt,
)
from app.prompts.defaults import (
    ANALYZE_COMPLIANCE_DEFAULT,
    COMPLIANCE_DEFAULT_VERSION,
    COMPLIANCE_PER_CRITERION_V2_DEFAULT,
    DEFAULTS,
)
from app.routes.prompts import _placeholders_in, _validate_template

REQUIRED = {"framework_name", "criteria_block", "max_idx"}
PER_CRITERION_V2_REQUIRED = {
    "framework_name",
    "criterion_id",
    "criterion_text",
    "document_text",
    "why_it_matters",
    "what_pass_looks_like",
}


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


# ── Per-criterion v2 — rationale block ────────────────────────────────


def test_per_criterion_v2_default_contains_required_placeholders():
    """Catch a regression where someone removes a placeholder from the v2
    template — the runtime .format() call would KeyError at request time."""
    placeholders = _placeholders_in(COMPLIANCE_PER_CRITERION_V2_DEFAULT)
    missing = PER_CRITERION_V2_REQUIRED - placeholders
    assert not missing, (
        f"v2 per-criterion default is missing required placeholders: {missing}."
    )


def test_per_criterion_v2_catalogue_placeholders_match_default():
    spec = DEFAULTS["compliance_per_criterion_v2"]
    assert set(spec["placeholders"]) == PER_CRITERION_V2_REQUIRED


def test_per_criterion_v1_still_registered():
    """v1 stays registered so user-saved overrides on the old key keep
    resolving instead of 404-ing the analyze run."""
    assert "compliance_per_criterion_v1" in DEFAULTS


def test_per_criterion_renders_both_rationale_lines_when_present():
    rendered = build_per_criterion_prompt(
        framework_name="AI Compliance Check",
        criterion_id="Q1-S-AI-1.1",
        criterion_text="Is an EIA completed before deployment?",
        document_text="(no document)",
        why_it_matters="Without an EIA, biases surface in production.",
        what_pass_looks_like="A signed Ethical Impact Assessment per SDAIA.",
    )
    assert "Why this matters: Without an EIA, biases surface in production." in rendered
    assert (
        "What a pass looks like: A signed Ethical Impact Assessment per SDAIA."
        in rendered
    )
    # Header order: rationale lines come AFTER `Criterion:` and BEFORE
    # `Architecture description`.
    why_idx = rendered.index("Why this matters:")
    pass_idx = rendered.index("What a pass looks like:")
    arch_idx = rendered.index("Architecture description")
    crit_idx = rendered.index("Criterion: Is an EIA completed")
    assert crit_idx < why_idx < pass_idx < arch_idx


def test_per_criterion_omits_label_when_only_why_present():
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="text",
        document_text="(no document)",
        why_it_matters="risk only",
        what_pass_looks_like=None,
    )
    assert "Why this matters: risk only" in rendered
    # The label-only line must not survive — no orphan "What a pass looks like:".
    assert "What a pass looks like:" not in rendered


def test_per_criterion_omits_label_when_only_pass_present():
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="text",
        document_text="(no document)",
        why_it_matters=None,
        what_pass_looks_like="pass only",
    )
    assert "What a pass looks like: pass only" in rendered
    assert "Why this matters:" not in rendered


def test_per_criterion_omits_both_when_both_null():
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="just the criterion",
        document_text="(no document)",
        why_it_matters=None,
        what_pass_looks_like=None,
    )
    # Neither label survives; no orphan "null" or empty-content line.
    assert "Why this matters:" not in rendered
    assert "What a pass looks like:" not in rendered
    assert "null" not in rendered.split("Architecture description", 1)[0]


def test_per_criterion_treats_whitespace_only_as_empty():
    """A whitespace-only rationale value should be stripped to empty and
    its label-only line removed — guards against UI bugs that save '   '."""
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="text",
        document_text="(no document)",
        why_it_matters="   \t  ",
        what_pass_looks_like="pass present",
    )
    assert "Why this matters:" not in rendered
    assert "What a pass looks like: pass present" in rendered


def test_per_criterion_handles_curly_braces_in_rationale():
    """Curly braces in the substituted VALUE must not be re-interpreted by
    str.format. Guard against a regression where someone reaches for a
    second .format() pass on the rendered text."""
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="text",
        document_text="(no document)",
        why_it_matters="contains {placeholder} and {another}",
        what_pass_looks_like="JSON like {\"a\": 1}",
    )
    assert "{placeholder}" in rendered
    assert "{another}" in rendered
    assert '{"a": 1}' in rendered


def test_per_criterion_handles_quotes_and_apostrophes():
    rendered = build_per_criterion_prompt(
        framework_name='Framework "X"',
        criterion_id="Q1",
        criterion_text="It's a question",
        document_text="(no document)",
        why_it_matters="vendor's lock-in is a problem",
        what_pass_looks_like='An "exit plan" document',
    )
    assert 'Framework: "Framework "X""' in rendered
    assert "vendor's lock-in" in rendered
    assert '"exit plan"' in rendered


def test_per_criterion_uses_explicit_template_when_provided():
    """Mirrors the override path: when the orchestrator passes a saved
    user template, the builder uses that, not the module's default."""
    custom = (
        "OVERRIDE\n"
        "fw={framework_name}\n"
        "cid={criterion_id}\n"
        "ctxt={criterion_text}\n"
        "doc={document_text}\n"
        "Why this matters: {why_it_matters}\n"
        "What a pass looks like: {what_pass_looks_like}\n"
        "END\n"
    )
    rendered = build_per_criterion_prompt(
        framework_name="X",
        criterion_id="Q1",
        criterion_text="text",
        document_text="doc",
        why_it_matters="risk",
        what_pass_looks_like="pass",
        template=custom,
    )
    assert rendered.startswith("OVERRIDE")
    assert "Why this matters: risk" in rendered
    assert "What a pass looks like: pass" in rendered


def test_per_criterion_q1_s_ai_1_1_full_render_snapshot():
    """Snapshot test: render the full v2 prompt for a real AI criterion
    using the seeded rationale text and assert key substrings. Captured
    in the PR description as the load-bearing evidence that the prompt
    actually carries the rationale through to Ollama."""
    rendered = build_per_criterion_prompt(
        framework_name="Artificial Intelligence (AI) Compliance Check",
        criterion_id="Q1-S-AI-1.1",
        criterion_text=(
            "Is an ethical impact assessment completed and formally approved "
            "before deployment or any material change?"
        ),
        document_text="(no document text provided)",
        why_it_matters=(
            "Without an EIA, biases, fairness gaps, and rights-affecting harms "
            "surface in production where remediation is expensive and may breach "
            "SDAIA AI ethics obligations."
        ),
        what_pass_looks_like=(
            "A signed Ethical Impact Assessment per SDAIA AI Ethics Principles, "
            "dated before go-live, with approval signature from the AI governance "
            "committee or accountable authority."
        ),
    )
    assert 'Framework: "Artificial Intelligence (AI) Compliance Check"' in rendered
    assert "Criterion ID: Q1-S-AI-1.1" in rendered
    assert "Why this matters: Without an EIA" in rendered
    assert "What a pass looks like: A signed Ethical Impact Assessment" in rendered
    # Hard rules and JSON-output discipline preserved from v1.
    assert "EVIDENCE RULE (mandatory)" in rendered
    assert "Output ONLY the JSON object." in rendered
