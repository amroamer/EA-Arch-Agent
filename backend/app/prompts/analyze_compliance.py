"""Compliance-mode prompt — score one architecture against ONE framework.

The default template (with `{framework_name}`, `{criteria_block}`,
`{max_idx}`) lives in `app.prompts.defaults.ANALYZE_COMPLIANCE_DEFAULT`.

The model is asked to produce two delimited sections per call:

    <NARRATIVE>
    ...markdown analysis focused on THIS framework's concerns...
    </NARRATIVE>
    <SCORECARD>
    [{"idx":0,"compliance_pct":100,"remarks":"..."}, ...]
    </SCORECARD>

Backend parses the live token stream as a small state machine, emits
narrative_token / scorecard_row SSE events.

Compliance values are categorical (matches the source spreadsheets):
    100 = Compliant
     50 = Partially Compliant
      0 = Not Compliant
   null = Not Applicable to this architecture

The /analyze endpoint runs ONE of these per selected framework, sequentially.
"""
from __future__ import annotations

from app.prompts.defaults import ANALYZE_COMPLIANCE_DEFAULT as _DEFAULT_TEMPLATE


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


__all__ = ["build_compliance_prompt"]
