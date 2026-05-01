"""Detailed analysis — full deep-dive across six dimensions.

The default template lives in `app.prompts.defaults.ANALYZE_DETAILED_DEFAULT`.
The user-selected `focus_areas` list is APPENDED at runtime (not part of
the template body) so the user-editable prompt stays focused on the
analysis structure.
"""
from __future__ import annotations

from app.prompts.defaults import ANALYZE_DETAILED_DEFAULT as PROMPT


def build_detailed_prompt(
    focus_areas: list[str] | None = None,
    *,
    template: str | None = None,
) -> str:
    """Append a focus-areas hint to the resolved template if any are selected."""
    base = template if template is not None else PROMPT
    if not focus_areas:
        return base
    formatted = ", ".join(focus_areas)
    return (
        base
        + f"\n\nThe user has prioritized these focus areas: {formatted}. "
        "Spend more depth on these dimensions, but still touch on the others briefly."
    )


__all__ = ["PROMPT", "build_detailed_prompt"]
