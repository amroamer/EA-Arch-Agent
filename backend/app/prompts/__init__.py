"""System prompts for each Analyze mode and the Compare endpoint.

These are kept as separate modules so they can be tuned without touching
business logic. Prompts are sourced verbatim from PRD §8 (subject to small
formatting normalizations — Markdown indentation, persona substitution).
"""
from app.prompts.analyze_quick import PROMPT as ANALYZE_QUICK
from app.prompts.analyze_detailed import PROMPT as ANALYZE_DETAILED
from app.prompts.analyze_persona import (
    PERSONA_DESCRIPTIONS,
    build_persona_prompt,
)
from app.prompts.analyze_user_driven import build_user_driven_prompt
from app.prompts.analyze_compliance import build_compliance_prompt
from app.prompts.compare import build_compare_prompt

__all__ = [
    "ANALYZE_QUICK",
    "ANALYZE_DETAILED",
    "PERSONA_DESCRIPTIONS",
    "build_persona_prompt",
    "build_user_driven_prompt",
    "build_compliance_prompt",
    "build_compare_prompt",
]
