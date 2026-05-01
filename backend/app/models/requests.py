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
