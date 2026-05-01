"""Persona-based analysis — view through one of four professional lenses.

The default template (with `{label}` and `{description}` placeholders)
lives in `app.prompts.defaults.ANALYZE_PERSONA_DEFAULT`. Persona
descriptions and display labels are still constants in this module —
they are data about the personas, not about how to analyse, and aren't
exposed in the prompt-editor UI.
"""
from __future__ import annotations

from app.prompts.defaults import ANALYZE_PERSONA_DEFAULT as _DEFAULT_TEMPLATE


PERSONA_DESCRIPTIONS: dict[str, str] = {
    "data": (
        "A Data Architect responsible for data modeling, data governance, "
        "data quality, master data, data lineage, and data lifecycle management."
    ),
    "network": (
        "A Network Architect responsible for network topology, segmentation, "
        "routing, peering, latency, throughput, and network security controls."
    ),
    "security": (
        "A Security Architect responsible for IAM, encryption, secrets "
        "management, vulnerability management, threat modeling, and compliance posture."
    ),
    "enterprise": (
        "An Enterprise Architect responsible for alignment with business "
        "strategy, integration patterns, technology standards, and architectural governance."
    ),
}

PERSONA_LABELS: dict[str, str] = {
    "data": "Data Architect",
    "network": "Network Architect",
    "security": "Security Architect",
    "enterprise": "Enterprise Architect",
}


def build_persona_prompt(persona: str, *, template: str | None = None) -> str:
    if persona not in PERSONA_DESCRIPTIONS:
        raise ValueError(f"Unknown persona: {persona!r}")
    tpl = template if template is not None else _DEFAULT_TEMPLATE
    return tpl.format(
        label=PERSONA_LABELS[persona],
        description=PERSONA_DESCRIPTIONS[persona],
    )


__all__ = [
    "PERSONA_DESCRIPTIONS",
    "PERSONA_LABELS",
    "build_persona_prompt",
]
