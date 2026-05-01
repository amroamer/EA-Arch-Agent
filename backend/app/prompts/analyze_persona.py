"""Persona-based analysis — view through one of four professional lenses.

Verbatim from PRD §8 `analyze_persona.py`, with persona descriptions
drawn from the same section.
"""

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

_TEMPLATE = """You are acting as a {label} reviewing the provided architecture diagram. Apply the lens, priorities, and concerns specific to a {label} role.

PERSONA: {description}

Produce:
## Persona-Specific Assessment
What does this architecture look like through the eyes of a {label}?

## Strengths from a {label} Perspective

## Concerns and Gaps from a {label} Perspective

## {label}-Specific Recommendations

## Roadmap

Reference frameworks and standards relevant to the persona (e.g. for Security Architect: NIST CSF, ISO 27001, SDAIA NCA; for Data Architect: DAMA-DMBOK, NDMO; for Network Architect: TOGAF, Zero Trust; for Enterprise Architect: TOGAF, Zachman)."""


def build_persona_prompt(persona: str) -> str:
    if persona not in PERSONA_DESCRIPTIONS:
        raise ValueError(f"Unknown persona: {persona!r}")
    return _TEMPLATE.format(
        label=PERSONA_LABELS[persona],
        description=PERSONA_DESCRIPTIONS[persona],
    )
