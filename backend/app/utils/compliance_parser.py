"""Streaming parser for compliance-mode model output.

The model emits two delimited sections per call:

    <NARRATIVE>
    ...markdown...
    </NARRATIVE>
    <SCORECARD>
    [{"idx":0,"compliance_pct":100,"remarks":"..."}, ...]
    </SCORECARD>

Tokens arrive in arbitrary chunks; tags can be split across chunks, and JSON
objects can span multiple tokens. This parser is a small state machine that
buffers, recognizes tag boundaries, and parses scorecard objects as soon as
each `{...}` is complete.

Public API:
    parser = ComplianceStreamParser()
    for token in tokens:
        for evt in parser.feed(token):
            ... # evt is one of: {"type": "narrative_token", "content"}
                #                {"type": "scorecard_row", "idx", "compliance_pct", "remarks"}
    for evt in parser.flush():  # consume any remaining narrative buffer
        ...
"""
from __future__ import annotations

import json
from typing import Any

NARRATIVE_OPEN = "<NARRATIVE>"
NARRATIVE_CLOSE = "</NARRATIVE>"
SCORECARD_OPEN = "<SCORECARD>"
SCORECARD_CLOSE = "</SCORECARD>"


class ComplianceStreamParser:
    """Stateful streaming parser. Feed token chunks; receive events."""

    def __init__(self) -> None:
        self.state: str = "INITIAL"  # INITIAL | NARRATIVE | BETWEEN | SCORECARD | DONE
        self._buf: str = ""
        self.narrative_text: str = ""  # accumulated for storage after stream
        self.parsed_indices: set[int] = set()

    # ── Public ────────────────────────────────────────────────────────────

    def feed(self, chunk: str) -> list[dict[str, Any]]:
        """Append `chunk` and return any events that became complete."""
        self._buf += chunk
        out: list[dict[str, Any]] = []
        while True:
            before = (self.state, len(self._buf))
            self._step(out)
            after = (self.state, len(self._buf))
            if before == after:
                break
        return out

    def flush(self) -> list[dict[str, Any]]:
        """Consume any pending narrative text in the buffer (called when the
        stream ends without closing tags — common when the model truncates).
        """
        out: list[dict[str, Any]] = []
        if self.state == "NARRATIVE" and self._buf:
            out.append({"type": "narrative_token", "content": self._buf})
            self.narrative_text += self._buf
            self._buf = ""
        return out

    # ── State machine ────────────────────────────────────────────────────

    def _step(self, out: list[dict[str, Any]]) -> None:
        if self.state == "INITIAL":
            self._look_for_open(NARRATIVE_OPEN, next_state="NARRATIVE")
        elif self.state == "NARRATIVE":
            self._consume_narrative(out)
        elif self.state == "BETWEEN":
            self._look_for_open(SCORECARD_OPEN, next_state="SCORECARD")
        elif self.state == "SCORECARD":
            self._consume_scorecard(out)
        # DONE: nothing to do, _buf can stay (we ignore trailing chatter)

    def _look_for_open(self, tag: str, *, next_state: str) -> None:
        idx = self._buf.find(tag)
        if idx >= 0:
            self._buf = self._buf[idx + len(tag) :]
            self.state = next_state
            return
        # Keep last (len(tag)-1) chars in case the tag is split mid-stream.
        keep = len(tag) - 1
        if len(self._buf) > keep:
            self._buf = self._buf[-keep:]

    def _consume_narrative(self, out: list[dict[str, Any]]) -> None:
        idx = self._buf.find(NARRATIVE_CLOSE)
        if idx >= 0:
            text = self._buf[:idx]
            if text:
                out.append({"type": "narrative_token", "content": text})
                self.narrative_text += text
            self._buf = self._buf[idx + len(NARRATIVE_CLOSE) :]
            self.state = "BETWEEN"
            return
        # Emit safe prefix (everything except the last tag-1 chars, which
        # might be the start of </NARRATIVE>).
        keep = len(NARRATIVE_CLOSE) - 1
        if len(self._buf) > keep:
            emit = self._buf[:-keep]
            out.append({"type": "narrative_token", "content": emit})
            self.narrative_text += emit
            self._buf = self._buf[-keep:]

    def _consume_scorecard(self, out: list[dict[str, Any]]) -> None:
        # Try to extract complete JSON objects one at a time.
        while True:
            obj, consumed = self._try_extract_object()
            if obj is None:
                break
            self._buf = self._buf[consumed:]
            if isinstance(obj, dict) and "idx" in obj:
                idx_val = obj["idx"]
                if isinstance(idx_val, int) and idx_val not in self.parsed_indices:
                    self.parsed_indices.add(idx_val)
                    out.append(
                        {
                            "type": "scorecard_row",
                            "idx": idx_val,
                            "compliance_pct": obj.get("compliance_pct"),
                            "remarks": (obj.get("remarks") or "").strip() or None,
                        }
                    )
        # Detect the closing tag.
        close_idx = self._buf.find(SCORECARD_CLOSE)
        if close_idx >= 0:
            self._buf = self._buf[close_idx + len(SCORECARD_CLOSE) :]
            self.state = "DONE"

    def _try_extract_object(self) -> tuple[Any, int]:
        """Locate the next complete `{...}` in the buffer and parse it.

        Returns (obj, chars_consumed_from_buffer_start). If no complete
        object is found, returns (None, 0).
        """
        start = self._buf.find("{")
        if start < 0:
            return None, 0
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(self._buf)):
            c = self._buf[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    snippet = self._buf[start : i + 1]
                    try:
                        return json.loads(snippet), i + 1
                    except json.JSONDecodeError:
                        # Skip past this `{` — try to recover from the next.
                        return None, start + 1
        return None, 0


def compute_weighted_score(items: list[dict[str, Any]]) -> float:
    """Per-framework weighted score: sum(weight*pct) / sum(weight) of applicable
    items, expressed as 0-100. N/A items (compliance_pct is None) are excluded
    from both sums (don't penalize for criteria that don't apply).
    """
    num = 0.0
    denom = 0.0
    for it in items:
        pct = it.get("compliance_pct")
        if pct is None:
            continue
        w = float(it.get("weight_planned", 0) or 0)
        num += w * float(pct)
        denom += w
    return (num / denom) if denom > 0 else 0.0
