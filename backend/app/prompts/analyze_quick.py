"""Quick analysis — concise high-level review under ~600 words.

The default template lives in `app.prompts.defaults.ANALYZE_QUICK_DEFAULT`.
At request time, the analyze route calls `fetch_template(db,
"analyze_quick")` which honours the user's saved override (Settings →
Prompts) before falling back to the default. The route then passes that
string in here as the `template` kwarg.

`PROMPT` (the default value, kept for any importer that wants the
constant directly) is re-exported from defaults for backwards
compatibility.
"""
from __future__ import annotations

from app.prompts.defaults import ANALYZE_QUICK_DEFAULT as PROMPT


def build_quick_prompt(*, template: str | None = None) -> str:
    """Quick mode has no placeholders — return the resolved template as-is."""
    return template if template is not None else PROMPT


__all__ = ["PROMPT", "build_quick_prompt"]
