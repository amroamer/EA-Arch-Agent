"""Compliance-mode prompt — score one architecture against ONE framework.

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
) -> str:
    """Return the system prompt for one framework's compliance evaluation.

    `items` is a list of dicts with at least {criteria, weight_planned}.
    The model identifies items by their zero-based index in this list.
    """
    criteria_block = _format_criteria(items)
    return f"""You are an Enterprise-Architecture compliance auditor. You will be given a single architecture diagram and a numbered list of compliance criteria from the "{framework_name}" framework. Score the architecture against each criterion.

Produce your response in EXACTLY two delimited sections, in this order:

<NARRATIVE>
A focused Markdown analysis of how the architecture stacks up against THIS framework's concerns. Cover:
- Strengths the architecture demonstrates relative to {framework_name}
- Gaps and risks the criteria expose
- Concrete recommendations to improve compliance with {framework_name}

Keep it tight — three short sections is plenty. Do NOT mention criterion indices in the narrative.
</NARRATIVE>
<SCORECARD>
A JSON array with EXACTLY one object per criterion, in the original order. Each object has:
  "idx":             integer (the [N] index from the list below — must be unique and 0..{len(items) - 1})
  "compliance_pct":  one of 100, 50, 0, or null
                       100  = Compliant (fully satisfied by the architecture)
                       50   = Partially Compliant
                       0    = Not Compliant
                       null = Not Applicable to this architecture
  "remarks":         short text (≤200 chars) explaining the score; cite specifics from the diagram

Return the array on a single line if possible, but it's OK to break across lines per object. Output ONLY the JSON — no commentary, no code fences inside this section.
</SCORECARD>

Compliance criteria for "{framework_name}":
{criteria_block}

Output ONLY the two delimited sections. Do not add any preamble, code fences, or extra text outside them."""
