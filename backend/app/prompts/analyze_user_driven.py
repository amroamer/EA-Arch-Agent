"""User-driven analysis — answer the user's specific question only.

The default template (with `{user_prompt}`) lives in
`app.prompts.defaults.ANALYZE_USER_DRIVEN_DEFAULT`.
"""
from __future__ import annotations

from app.prompts.defaults import ANALYZE_USER_DRIVEN_DEFAULT as _DEFAULT_TEMPLATE


def build_user_driven_prompt(
    user_prompt: str, *, template: str | None = None
) -> str:
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt is required for user_driven mode")
    tpl = template if template is not None else _DEFAULT_TEMPLATE
    return tpl.format(user_prompt=user_prompt.strip())


__all__ = ["build_user_driven_prompt"]
