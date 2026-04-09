"""
"A man uses the same blade for every kill."
Central LLM factory so every call site gets the same defaults:
  - model
  - temperature
  - max_tokens (critical — default is too low for structured bootstrap)
  - timeout
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model

from src.config import LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT


def get_llm(**overrides):
    """Build a configured chat model with our defaults."""
    params = {
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "timeout": LLM_TIMEOUT,
    }
    params.update(overrides)
    return init_chat_model(LLM_MODEL, **params)
