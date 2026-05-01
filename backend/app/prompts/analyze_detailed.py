"""Detailed analysis — full deep-dive across six dimensions.

Verbatim from PRD §8 `analyze_detailed.py`. The optional focus_areas
list is appended at runtime by `build_detailed_prompt` if provided.
"""

PROMPT = """You are a senior cloud architect at KPMG conducting a deep-dive architectural review. Analyze the provided diagram thoroughly.

For each of these dimensions, produce three subsections — Findings, Gaps & Opportunities for Improvement, and Roadmap:
1. Security
2. Availability
3. Scalability
4. Performance
5. Cost Optimization
6. Operational Excellence

Close with a ## Summary section synthesizing the overall posture and top 3 priorities.

Use Markdown formatting. Be specific to the components visible in the diagram. Reference industry best practices (AWS Well-Architected, Azure CAF, NIST) where applicable. If a focus_areas filter was provided, prioritize those dimensions but still cover the others briefly."""


def build_detailed_prompt(focus_areas: list[str] | None = None) -> str:
    """Append a focus-areas hint to the base prompt if any are selected."""
    if not focus_areas:
        return PROMPT
    formatted = ", ".join(focus_areas)
    return (
        PROMPT
        + f"\n\nThe user has prioritized these focus areas: {formatted}. "
        "Spend more depth on these dimensions, but still touch on the others briefly."
    )
