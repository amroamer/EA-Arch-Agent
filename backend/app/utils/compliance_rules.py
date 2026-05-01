"""Server-side rules applied to per-criterion compliance verdicts before
they are streamed to the client and persisted.

Currently one rule:

    Evidence-enforcement — a `compliance_pct` of 100 (Compliant) MUST
    carry a non-empty, non-"none", non-punctuation evidence citation.
    If the model returns a 100 with empty / "none" / placeholder
    evidence, downgrade to 50 (Partial) and prepend an explanatory
    note to the remarks.

Pure functions — no I/O — so they're trivially unit-testable.
"""
from __future__ import annotations

import re
from typing import Any

# Tokens that look like a citation but actually mean "I have nothing".
# Match case-insensitively against the trimmed evidence string.
_PLACEHOLDER_EVIDENCE = {
    "",
    "none",
    "n/a",
    "na",
}

# Strings consisting only of punctuation / dashes / whitespace are
# treated as no evidence.
_PUNCT_ONLY_RE = re.compile(r"^[\s\-–—\.\,\;\:\!\?]*$")

# Marker prepended to remarks when we downgrade — used both to signal
# the change and to make the rule idempotent (we don't re-prepend).
_DOWNGRADE_NOTE = (
    "[Server downgrade: no concrete evidence cited for a Compliant verdict.]"
)


def _evidence_is_empty(evidence: Any) -> bool:
    """Treat empty / whitespace / 'none' / dashes as 'no evidence'."""
    if evidence is None:
        return True
    if not isinstance(evidence, str):
        return True
    stripped = evidence.strip()
    if stripped.lower() in _PLACEHOLDER_EVIDENCE:
        return True
    return bool(_PUNCT_ONLY_RE.match(stripped))


def _enforce_evidence_rule(verdict: dict[str, Any]) -> dict[str, Any]:
    """Apply the evidence rule. Returns a NEW dict; does not mutate input.

    - compliance_pct == 100 with empty evidence → 50, note prepended.
    - All other inputs returned unchanged (shallow-copied).
    - Idempotent: applying twice produces the same result as once.
    """
    out = dict(verdict)  # shallow copy — we don't mutate the caller's dict

    if out.get("compliance_pct") != 100:
        return out

    if not _evidence_is_empty(out.get("evidence")):
        return out

    # Downgrade.
    out["compliance_pct"] = 50

    remarks = (out.get("remarks") or "").strip()
    if _DOWNGRADE_NOTE in remarks:
        # Already noted (idempotency).
        out["remarks"] = remarks
    elif remarks:
        out["remarks"] = f"{_DOWNGRADE_NOTE} {remarks}"
    else:
        out["remarks"] = _DOWNGRADE_NOTE

    return out


__all__ = ["_enforce_evidence_rule"]
