"""Pick an LLM adapter from settings. Falls back to NullLLM (no key required)."""
from __future__ import annotations

from ..config import Settings
from .null_llm import NullLLM


def make_llm(settings: Settings):
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        from .anthropic_adapter import AnthropicLLM
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    # ollama / openai adapters plug in here later.
    return NullLLM()
