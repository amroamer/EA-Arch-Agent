"""Pydantic request models and enums for the API surface."""
from __future__ import annotations

from enum import Enum


class AnalysisMode(str, Enum):
    QUICK = "quick"
    DETAILED = "detailed"
    PERSONA = "persona"
    USER_DRIVEN = "user_driven"
    COMPLIANCE = "compliance"


class Persona(str, Enum):
    DATA = "data"
    NETWORK = "network"
    SECURITY = "security"
    ENTERPRISE = "enterprise"


class SessionType(str, Enum):
    ANALYZE = "analyze"
    COMPARE = "compare"


class SessionStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class ScoringMode(str, Enum):
    """Compliance-mode scoring strategy.

    - SINGLE_PASS: one Ollama call per framework producing NARRATIVE +
      SCORECARD for all criteria at once. Original implementation.
    - PER_CRITERION: one Ollama call PER criterion (focused JSON verdict),
      followed by one synthesis call per framework for the narrative.
      Enables incremental UI updates and tighter per-criterion scoring.
    """

    SINGLE_PASS = "single_pass"
    PER_CRITERION = "per_criterion"
