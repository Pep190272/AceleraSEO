import pytest

from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.llm.factory import _is_real_key, make_llm
from aceleraseo.infrastructure.llm.null_llm import NullLLM


def _settings(**kw):
    base = dict(anthropic_api_key="", llm_provider="anthropic")
    base.update(kw)
    return Settings(**base)


def test_no_key_uses_null_llm():
    assert isinstance(make_llm(_settings(anthropic_api_key="")), NullLLM)


def test_placeholder_key_uses_null_llm():
    # The shipped .env.example placeholder must NOT select the real adapter.
    assert isinstance(make_llm(_settings(anthropic_api_key="YOUR_ANTHROPIC_API_KEY")), NullLLM)
    assert isinstance(make_llm(_settings(anthropic_api_key="sk-PLACEHOLDER")), NullLLM)


def test_real_key_passes_the_key_guard():
    # The selection decision is what matters and is dependency-free; instantiating
    # the real adapter needs the optional `anthropic` package, so don't require it.
    assert _is_real_key("sk-ant-api03-genuinevalue123") is True
    assert _is_real_key("YOUR_ANTHROPIC_API_KEY") is False
    assert _is_real_key("") is False


def test_real_key_selects_anthropic_adapter():
    pytest.importorskip("anthropic")  # skip cleanly if the optional dep is absent
    llm = make_llm(_settings(anthropic_api_key="sk-ant-api03-genuinevalue123"))
    assert not isinstance(llm, NullLLM)
    assert type(llm).__name__ == "AnthropicLLM"
