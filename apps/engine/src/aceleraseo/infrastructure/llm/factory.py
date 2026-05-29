"""Pick an LLM adapter from settings. Falls back to NullLLM (no key required)."""
from __future__ import annotations

from ..config import Settings
from .null_llm import NullLLM


def _is_real_key(value: str) -> bool:
    """A configured key must be non-empty AND not a placeholder.

    The shipped .env.example uses YOUR_*_HERE placeholders. Treating those as a
    real key selected the Anthropic adapter, which then 500'd on the first call.
    A placeholder must behave exactly like 'no key' -> NullLLM.
    """
    if not value:
        return False
    upper = value.upper()
    return not (upper.startswith("YOUR_") or "PLACEHOLDER" in upper or value == "change-me")


def make_llm(settings: Settings):
    if settings.llm_provider == "anthropic" and _is_real_key(settings.anthropic_api_key):
        from .anthropic_adapter import AnthropicLLM
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    # ollama / openai adapters plug in here later.
    return NullLLM()


def make_discoverer(settings: Settings):
    """Keyword discoverer, or None if no real LLM key (e.g. demo mode)."""
    if settings.llm_provider == "anthropic" and _is_real_key(settings.anthropic_api_key):
        from .discoverer import AnthropicKeywordDiscoverer
        return AnthropicKeywordDiscoverer(settings.anthropic_api_key, settings.anthropic_model)
    return None


def make_market(settings: Settings):
    """DataForSEO market provider, or None if credentials are absent."""
    if _is_real_key(settings.dataforseo_login) and _is_real_key(settings.dataforseo_password):
        from ..providers.dataforseo import DataForSEOMarketProvider
        return DataForSEOMarketProvider(settings.dataforseo_login, settings.dataforseo_password)
    return None
