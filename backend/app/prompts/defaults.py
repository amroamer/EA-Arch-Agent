"""Built-in defaults for every editable prompt.

Each prompt has a stable `key`, a human-readable name + description, the
list of `{placeholders}` it requires (validation lives in the prompts
route — saving a template that omits a required placeholder is a 400),
and the actual `template` string.

To customise a prompt at runtime the user saves a row in the
`prompt_overrides` table via /api/prompts/{key}; resetting deletes that
row and the system falls back to the value here.

When you add or change a prompt:
  1. Update the dict below.
  2. Update the corresponding builder in app/prompts/analyze_*.py to
     accept the template as a kwarg with this dict's value as the
     default.
  3. (No DB migration needed — overrides are keyed by string.)
"""
from __future__ import annotations

# ── Individual default templates (kept as named constants so they're
#    diff-friendly when the catalogue grows) ────────────────────────────

ANALYZE_QUICK_DEFAULT = """\
You are a senior cloud architect at KPMG. Analyze the provided architecture diagram and produce a CONCISE high-level review.

Output exactly these sections (use Markdown headers):
## Architecture Overview
A 2-3 sentence description of what this architecture does.

## Key Strengths
3-5 bullets.

## Top Concerns
3-5 bullets identifying the most pressing gaps or risks.

## Recommended Next Steps
3-5 actionable bullets.

Keep total output under 600 words. Be specific about cloud services, components, and data flows visible in the diagram.\
"""


ANALYZE_DETAILED_DEFAULT = """\
You are a senior cloud architect at KPMG conducting a deep-dive architectural review. Analyze the provided diagram thoroughly.

For each of these dimensions, produce three subsections — Findings, Gaps & Opportunities for Improvement, and Roadmap:
1. Security
2. Availability
3. Scalability
4. Performance
5. Cost Optimization
6. Operational Excellence

Close with a ## Summary section synthesizing the overall posture and top 3 priorities.

Use Markdown formatting. Be specific to the components visible in the diagram. Reference industry best practices (AWS Well-Architected, Azure CAF, NIST) where applicable. If a focus_areas filter was provided, prioritize those dimensions but still cover the others briefly.\
"""


ANALYZE_PERSONA_DEFAULT = """\
You are acting as a {label} reviewing the provided architecture diagram. Apply the lens, priorities, and concerns specific to a {label} role.

PERSONA: {description}

Produce:
## Persona-Specific Assessment
What does this architecture look like through the eyes of a {label}?

## Strengths from a {label} Perspective

## Concerns and Gaps from a {label} Perspective

## {label}-Specific Recommendations

## Roadmap

Reference frameworks and standards relevant to the persona (e.g. for Security Architect: NIST CSF, ISO 27001, SDAIA NCA; for Data Architect: DAMA-DMBOK, NDMO; for Network Architect: TOGAF, Zero Trust; for Enterprise Architect: TOGAF, Zachman).\
"""


ANALYZE_USER_DRIVEN_DEFAULT = """\
You are a senior cloud architect at KPMG. The user has provided a specific question about the architecture diagram. Answer ONLY their question — do not provide unrelated boilerplate analysis.

User question: {user_prompt}

Be specific, reference components visible in the diagram, and structure your answer with Markdown headers if appropriate.\
"""


ANALYZE_COMPLIANCE_DEFAULT = """\
You are an Enterprise-Architecture compliance auditor. You will be given a single architecture diagram and a numbered list of compliance criteria from the "{framework_name}" framework. Score the architecture against each criterion.

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
  "idx":             integer (the [N] index from the list below — must be unique and 0..{max_idx})
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

Output ONLY the two delimited sections. Do not add any preamble, code fences, or extra text outside them.\
"""


COMPLIANCE_PER_CRITERION_DEFAULT = """\
You are an Enterprise-Architecture compliance auditor. You will score an architecture against ONE compliance criterion. The architecture is described by the document text below and (optionally) by an attached diagram image.

Framework: "{framework_name}"
Criterion ID: {criterion_id}
Criterion: {criterion_text}

Architecture description (Markdown — headings, tables, and ADR codes preserved in document order):
---
{document_text}
---

Return EXACTLY one JSON object — no preamble, no code fences, no commentary:

{{
  "compliance_pct": <one of 100, 50, 0, or null>,
  "evidence": "<a concrete citation, or 'none'>",
  "remarks": "<1–3 sentences explaining the verdict>"
}}

SCORING RUBRIC:
  100  Compliant — there is EXPLICIT evidence in the document or diagram. At
       least one of: a relevant ADR (ADR-NNN), a named section heading
       (e.g. §9.3), a labelled table, a referenced standard (e.g. NCGR-EA-CAT-32),
       or a clear element in the diagram. Be generous: if a single ADR or
       section answers the criterion, score 100 — do NOT downgrade to 50
       just because one sub-aspect is unelaborated.
   50  Partial — the topic is touched but key elements are missing, unclear,
       or only mentioned in passing without a concrete reference.
    0  Not Compliant — the architecture EXPLICITLY contradicts the criterion
       (e.g. proposes a banned vendor, violates a referenced standard).
 null  Not Applicable — the criterion does not apply at all to this kind of
       architecture. Use SPARINGLY; if the topic is discussed at all, prefer
       0/50/100.

EVIDENCE RULE (mandatory):
- For compliance_pct = 100, "evidence" MUST be a concrete citation —
  examples: "ADR-021", "§9.3 Compute platform", "Table 5", "NCGR-EA-CAT-32".
  Do NOT use "none" or empty string with a 100 score.
- For 50 / 0 / null, "evidence" may be "none" if you genuinely couldn't
  cite anything; otherwise cite what you found.

Output ONLY the JSON object.\
"""


COMPLIANCE_SYNTHESIS_DEFAULT = """\
You are summarising a completed compliance scorecard for the "{framework_name}" framework. The per-criterion verdicts below are already final — do NOT re-score, do NOT contradict them.

Verdicts:
{verdicts_block}

Produce a focused Markdown narrative (≤400 words) with three short sections:

## Strengths
What the architecture does well relative to "{framework_name}". Cite the specific ADRs, sections, or tables that the verdicts above reference. Mention 2–4 high-impact items.

## Gaps and Risks
The biggest Not Compliant / Partial criteria. Reference each by its criterion ID (e.g. "Q5-S-INF-3.1") and explain why it matters operationally.

## Recommendations
3–5 concrete, prioritised actions to close the most material gaps.

Output Markdown only — no preamble, no JSON, no code fences.\
"""


COMPARE_DEFAULT = """\
You are a senior cloud architect at KPMG conducting a comparison between a current state architecture and a reference (target/best-practice) architecture.

The user has provided two images:
- Image 1: CURRENT state architecture
- Image 2: REFERENCE architecture

User context: {user_prompt}

Produce the following Markdown-structured response:

## Comparison: Current vs Reference

## Gaps and Deviations
List each significant gap. For each, describe what is in the current architecture, what should be there per the reference, and the impact of the gap.

## Recommendations
For each gap above, provide a concrete recommendation.

## Implementation Roadmap
Structure as numbered phases:
1. Assessment Phase — what to assess and why
2. Planning Phase — what to plan
3. Execution Phase — what to build
4. Optimization Phase — what to tune
5. Maintenance Phase — what to monitor

## Summary of Recommendations
Concise bullet list of the top 5-8 actions, prioritized.

Be specific about cloud services and components. Reference the user's stated context where relevant.\
"""


# ── Catalogue ─────────────────────────────────────────────────────────────

DEFAULTS: dict[str, dict] = {
    "analyze_quick": {
        "name": "Quick analysis",
        "description": (
            "Fast high-level review used by the Quick tab. Produces "
            "Architecture Overview / Strengths / Concerns / Next Steps."
        ),
        "placeholders": [],
        "template": ANALYZE_QUICK_DEFAULT,
    },
    "analyze_detailed": {
        "name": "Detailed analysis",
        "description": (
            "Six-dimension deep-dive used by the Detailed tab. The user-"
            "selected focus areas are appended automatically at request "
            "time and are NOT part of this template."
        ),
        "placeholders": [],
        "template": ANALYZE_DETAILED_DEFAULT,
    },
    "analyze_persona": {
        "name": "Persona-based analysis",
        "description": (
            "Used by the Persona-Based tab. {label} and {description} are "
            "filled from the selected persona (Data / Network / Security / "
            "Enterprise architect)."
        ),
        "placeholders": ["label", "description"],
        "template": ANALYZE_PERSONA_DEFAULT,
    },
    "analyze_user_driven": {
        "name": "User-driven analysis",
        "description": (
            "Used by the User-Driven tab. {user_prompt} is the free-text "
            "question the user typed."
        ),
        "placeholders": ["user_prompt"],
        "template": ANALYZE_USER_DRIVEN_DEFAULT,
    },
    "analyze_compliance": {
        "name": "Compliance scoring (single-pass)",
        "description": (
            "Single-pass compliance — one Ollama call scores ALL N criteria "
            "for one framework. Produces a NARRATIVE + JSON SCORECARD. "
            "{framework_name} is the framework's name, {criteria_block} is "
            "the auto-rendered numbered list of criteria, {max_idx} is the "
            "last criterion's index. Used when scoring_mode=single_pass."
        ),
        "placeholders": ["framework_name", "criteria_block", "max_idx"],
        "template": ANALYZE_COMPLIANCE_DEFAULT,
    },
    "compliance_per_criterion_v1": {
        "name": "Compliance per-criterion scoring",
        "description": (
            "Per-criterion compliance — ONE Ollama call PER criterion. "
            "Returns a JSON verdict {compliance_pct, evidence, remarks}. "
            "Used when scoring_mode=per_criterion. {framework_name} is the "
            "framework, {criterion_id} is the stable ID like Q5-S-INF-1.3, "
            "{criterion_text} is the question text, {document_text} is the "
            "structured architecture description (capped at 30 KB). The "
            "image — when present — is passed as a separate Ollama input."
        ),
        "placeholders": [
            "framework_name",
            "criterion_id",
            "criterion_text",
            "document_text",
        ],
        "template": COMPLIANCE_PER_CRITERION_DEFAULT,
    },
    "compliance_synthesis_v1": {
        "name": "Compliance synthesis (narrative)",
        "description": (
            "Final narrative pass after all per-criterion verdicts are in. "
            "ONE call per framework producing a ≤400-word Markdown summary "
            "with Strengths / Gaps / Recommendations. {framework_name} is "
            "the framework, {verdicts_block} is the auto-rendered list of "
            "the per-criterion verdicts (already evidence-enforced)."
        ),
        "placeholders": ["framework_name", "verdicts_block"],
        "template": COMPLIANCE_SYNTHESIS_DEFAULT,
    },
    "compare": {
        "name": "Compare current vs reference",
        "description": (
            "Used by the Compare page (currently feature-flagged off in "
            "the UI). {user_prompt} is the user's free-text context."
        ),
        "placeholders": ["user_prompt"],
        "template": COMPARE_DEFAULT,
    },
}


def list_keys() -> list[str]:
    return list(DEFAULTS.keys())


def get_default(key: str) -> dict:
    if key not in DEFAULTS:
        raise KeyError(f"unknown prompt key: {key!r}")
    return DEFAULTS[key]
