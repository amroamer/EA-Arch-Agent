"""Compare prompt — current vs reference architecture analysis.

The default template (with `{user_prompt}`) lives in
`app.prompts.defaults.COMPARE_DEFAULT`.
"""
from __future__ import annotations

from app.prompts.defaults import COMPARE_DEFAULT as _DEFAULT_TEMPLATE


def build_compare_prompt(user_prompt: str, *, template: str | None = None) -> str:
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt is required for compare")
    tpl = template if template is not None else _DEFAULT_TEMPLATE
    return tpl.format(user_prompt=user_prompt.strip())


__all__ = ["build_compare_prompt"]
