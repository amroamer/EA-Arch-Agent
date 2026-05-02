"""Compliance-mode prompts — single-pass and per-criterion builders.

Single-pass (`build_compliance_prompt`): one Ollama call scores all
criteria for a framework, producing both a NARRATIVE and SCORECARD block.
Default template at `app.prompts.defaults.ANALYZE_COMPLIANCE_DEFAULT`.

Per-criterion (`build_per_criterion_prompt`): one Ollama call per
criterion. Default template at
`app.prompts.defaults.COMPLIANCE_PER_CRITERION_V2_DEFAULT` — note the v2
default surfaces the rationale fields `why_it_matters` and
`what_pass_looks_like`. Empty rationale renders as no line at all (not as
a label with empty content).

Backend parses the single-pass live token stream as a small state machine,
emits narrative_token / scorecard_row SSE events.

Compliance values are categorical (matches the source spreadsheets):
    100 = Compliant
     50 = Partially Compliant
      0 = Not Compliant
   null = Not Applicable to this architecture

The /analyze endpoint runs ONE single-pass call per framework OR N
per-criterion calls plus a synthesis pass per framework, depending on the
client-supplied `scoring_mode`.
"""
from __future__ import annotations

import re

from app.prompts.defaults import (
    ANALYZE_COMPLIANCE_DEFAULT as _DEFAULT_TEMPLATE,
    COMPLIANCE_PER_CRITERION_V2_DEFAULT as _PER_CRITERION_DEFAULT_TEMPLATE,
)


def _format_criteria(items: list[dict]) -> str:
    """Render the framework's items as a numbered list for the prompt."""
    lines: list[str] = []
    for idx, it in enumerate(items):
        weight = it.get("weight_planned", 0)
        lines.append(f"  [{idx}] (weight {weight:g}%) {it['criteria']}")
    return "\n".join(lines)


def build_compliance_prompt(
    *,
    framework_name: str,
    items: list[dict],
    template: str | None = None,
) -> str:
    """Return the system prompt for one framework's compliance evaluation.

    `items` is a list of dicts with at least {criteria, weight_planned}.
    The model identifies items by their zero-based index in this list.
    """
    criteria_block = _format_criteria(items)
    tpl = template if template is not None else _DEFAULT_TEMPLATE
    return tpl.format(
        framework_name=framework_name,
        criteria_block=criteria_block,
        max_idx=max(0, len(items) - 1),
    )


# Match a rationale line whose value collapsed to empty whitespace after
# substitution. We strip the entire line (including its trailing newline)
# so the consultant doesn't see "Why this matters:" with nothing after it.
_EMPTY_WHY_LINE_RE = re.compile(r"^Why this matters:[ \t]*\n", re.MULTILINE)
_EMPTY_PASS_LINE_RE = re.compile(
    r"^What a pass looks like:[ \t]*\n", re.MULTILINE
)


def build_per_criterion_prompt(
    *,
    framework_name: str,
    criterion_id: str,
    criterion_text: str,
    document_text: str,
    why_it_matters: str | None = None,
    what_pass_looks_like: str | None = None,
    template: str | None = None,
) -> str:
    """Return the system prompt for one criterion's compliance evaluation.

    Empty / null rationale is substituted as the empty string and the
    resulting label-only line ("Why this matters:" with nothing after) is
    stripped. Both empty → both lines vanish; one empty → only that line
    vanishes; both populated → both render verbatim.
    """
    tpl = template if template is not None else _PER_CRITERION_DEFAULT_TEMPLATE
    rendered = tpl.format(
        framework_name=framework_name,
        criterion_id=criterion_id,
        criterion_text=criterion_text,
        document_text=document_text or "(no document text provided)",
        why_it_matters=(why_it_matters or "").strip(),
        what_pass_looks_like=(what_pass_looks_like or "").strip(),
    )
    rendered = _EMPTY_WHY_LINE_RE.sub("", rendered)
    rendered = _EMPTY_PASS_LINE_RE.sub("", rendered)
    return rendered


__all__ = ["build_compliance_prompt", "build_per_criterion_prompt"]
