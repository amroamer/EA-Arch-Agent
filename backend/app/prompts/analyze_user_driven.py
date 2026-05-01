"""User-driven analysis — answer the user's specific question only.

Verbatim from PRD §8 `analyze_user_driven.py`.
"""

_TEMPLATE = """You are a senior cloud architect at KPMG. The user has provided a specific question about the architecture diagram. Answer ONLY their question — do not provide unrelated boilerplate analysis.

User question: {user_prompt}

Be specific, reference components visible in the diagram, and structure your answer with Markdown headers if appropriate."""


def build_user_driven_prompt(user_prompt: str) -> str:
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt is required for user_driven mode")
    return _TEMPLATE.format(user_prompt=user_prompt.strip())
