from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.llm.factory import make_llm
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


def test_real_key_selects_anthropic_adapter():
    llm = make_llm(_settings(anthropic_api_key="sk-ant-api03-genuinevalue123"))
    assert not isinstance(llm, NullLLM)
    assert type(llm).__name__ == "AnthropicLLM"
