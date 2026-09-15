"""Tests for the Brave Search competitor adapter — no network required.

Brave HTTP calls are mocked via monkeypatching httpx.get; GSC rows come from a
FakeGSC stand-in for RankingProvider. Covers domain normalisation, seed-query
selection, aggregation math, own-domain exclusion, empty results, Brave
401/429/network errors (never leaking the key), the target != configured
property guard, and factory.make_competitor's DataForSEO/Brave/None order.
"""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from aceleraseo.domain.models import RankingSignal
from aceleraseo.infrastructure.providers.brave_competitors import (
    BraveCompetitorProvider,
    BraveSearchError,
    _extract_hosts,
    _normalize_domain,
    _top_queries_by_impressions,
)

_API_KEY = "brave-secret-key-do-not-log"


class FakeGSC:
    """Stand-in for domain.ports.RankingProvider."""

    def __init__(self, signals: list[RankingSignal]):
        self._signals = signals

    def fetch_rankings(self, site_url: str, days: int) -> list[RankingSignal]:
        return self._signals


def _signal(query: str, impressions: int) -> RankingSignal:
    return RankingSignal(
        query=query, page="/", position=5.0, clicks=1,
        impressions=impressions, ctr=0.1, observed_on=date(2026, 9, 1),
    )


class _Resp:
    def __init__(self, status_code: int, json_body: dict | None = None):
        self.status_code = status_code
        self._json = json_body or {}

    def json(self):
        return self._json


def _brave_results(*hosts: str) -> dict:
    return {"web": {"results": [{"url": f"https://{h}/page"} for h in hosts]}}


def _patch_brave(monkeypatch, responses):
    """responses: dict[query] -> _Resp, or one _Resp reused for every call."""
    def fake_get(url, params=None, headers=None, timeout=None):
        return responses[params["q"]] if isinstance(responses, dict) else responses

    monkeypatch.setattr(httpx, "get", fake_get)


def _provider(gsc_signals, site_url="sc-domain:example.com") -> BraveCompetitorProvider:
    return BraveCompetitorProvider(_API_KEY, FakeGSC(gsc_signals), site_url)


# ── pure helpers ────────────────────────────────────────────────

def test_normalize_domain_strips_scheme_www_and_sc_domain_prefix():
    assert _normalize_domain("https://www.Rival.com/path") == "rival.com"
    assert _normalize_domain("sc-domain:Example.com") == "example.com"
    assert _normalize_domain("example.com") == "example.com"


def test_top_queries_orders_by_impressions_and_limits():
    signals = [_signal("b", 10), _signal("a", 50), _signal("a", 10), _signal("c", 30)]
    assert _top_queries_by_impressions(signals, 10) == ["a", "c", "b"]
    assert _top_queries_by_impressions(signals, 2) == ["a", "c"]


def test_extract_hosts_preserves_order_and_handles_empty():
    assert _extract_hosts(_brave_results("first.com", "second.com")) == ["first.com", "second.com"]
    assert _extract_hosts({}) == []
    assert _extract_hosts({"web": {}}) == []


# ── BraveCompetitorProvider.fetch_competitors ─────────────────

def test_raises_when_target_is_not_the_configured_site():
    provider = _provider([])
    with pytest.raises(ValueError, match="different domain"):
        provider.fetch_competitors("other.com", "", "es", 5, 10)


def test_returns_empty_when_no_gsc_queries():
    assert _provider([]).fetch_competitors("example.com", "", "es", 5, 10) == []


def test_aggregates_common_keywords_avg_position_and_orders(monkeypatch):
    provider = _provider([_signal("q1", 100), _signal("q2", 50)])
    _patch_brave(monkeypatch, {
        "q1": _Resp(200, _brave_results("rival.com", "other.com")),
        "q2": _Resp(200, _brave_results("rival.com", "other.com")),
    })
    result = provider.fetch_competitors("example.com", "", "es", 5, 10)

    by_domain = {c.domain: c for c in result}
    assert by_domain["rival.com"].common_keywords == 2
    assert by_domain["rival.com"].avg_position == 1.0
    assert by_domain["other.com"].avg_position == 2.0
    # both tie on common_keywords -> better (lower) avg_position sorts first
    assert result[0].domain == "rival.com"
    assert result[0].organic_traffic == 0
    assert result[0].ranked_keywords[0].search_volume == 0


def test_excludes_target_and_normalizes_www(monkeypatch):
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(200, _brave_results("www.example.com", "rival.com")))
    result = provider.fetch_competitors("example.com", "", "es", 5, 10)
    assert [c.domain for c in result] == ["rival.com"]


def test_respects_max_competitors_and_max_keywords(monkeypatch):
    provider = _provider([_signal(f"q{i}", 100 - i) for i in range(4)])
    _patch_brave(monkeypatch, _Resp(200, _brave_results("a.com", "b.com", "c.com")))
    result = provider.fetch_competitors("example.com", "", "es", max_competitors=2, max_keywords_per_competitor=1)
    assert len(result) == 2
    assert all(len(c.ranked_keywords) == 1 for c in result)


def test_empty_brave_results_yield_no_competitors(monkeypatch):
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(200, {}))
    assert provider.fetch_competitors("example.com", "", "es", 5, 10) == []


def test_duplicate_domain_in_one_query_counts_once(monkeypatch):
    """Brave can return several URLs from the same domain for one query — that
    must not inflate common_keywords or repeat the same keyword."""
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(200, _brave_results("rival.com", "rival.com", "other.com")))
    result = provider.fetch_competitors("example.com", "", "es", 5, 10)
    by_domain = {c.domain: c for c in result}
    assert by_domain["rival.com"].common_keywords == 1
    assert by_domain["rival.com"].avg_position == 1.0  # kept the best (first) rank
    assert len(by_domain["rival.com"].ranked_keywords) == 1


def test_malformed_brave_response_raises_brave_search_error(monkeypatch):
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(200, {"web": {"results": "not-a-list"}}))
    with pytest.raises(BraveSearchError, match="unexpected response shape"):
        provider.fetch_competitors("example.com", "", "es", 5, 10)


# ── Brave error handling ───────────────────────────────────────

def test_401_raises_clear_error_without_leaking_key(monkeypatch):
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(401))
    with pytest.raises(BraveSearchError) as exc_info:
        provider.fetch_competitors("example.com", "", "es", 5, 10)
    assert "401" in str(exc_info.value)
    assert _API_KEY not in str(exc_info.value)


def test_429_raises_clear_error(monkeypatch):
    provider = _provider([_signal("q1", 10)])
    _patch_brave(monkeypatch, _Resp(429))
    with pytest.raises(BraveSearchError, match="429"):
        provider.fetch_competitors("example.com", "", "es", 5, 10)


def test_network_error_raises_brave_search_error(monkeypatch):
    provider = _provider([_signal("q1", 10)])

    def raise_network(*args, **kwargs):
        raise httpx.ConnectTimeout("boom")

    monkeypatch.setattr(httpx, "get", raise_network)
    with pytest.raises(BraveSearchError, match="Could not reach"):
        provider.fetch_competitors("example.com", "", "es", 5, 10)


# ── factory.make_competitor selection order ────────────────────

def _settings(**overrides):
    from aceleraseo.infrastructure.config import Settings
    return Settings(_env_file=None, **overrides)


def test_factory_prefers_dataforseo_when_real_creds():
    from aceleraseo.infrastructure.llm.factory import make_competitor
    from aceleraseo.infrastructure.providers.dataforseo import DataForSEOMarketProvider

    settings = _settings(
        dataforseo_login="real-login", dataforseo_password="real-pass",
        brave_api_key="real-brave-key", gsc_site_url="sc-domain:example.com",
    )
    assert isinstance(make_competitor(settings), DataForSEOMarketProvider)


def test_factory_returns_brave_provider_when_key_real_connected_and_site_set(monkeypatch):
    from aceleraseo.infrastructure.google import oauth
    from aceleraseo.infrastructure.llm import factory

    monkeypatch.setattr(oauth, "load_credentials", lambda settings: object())
    monkeypatch.setattr(
        "aceleraseo.infrastructure.google.gsc_adapter.GSCRankingProvider",
        lambda credentials: "fake-gsc-provider",
    )
    settings = _settings(brave_api_key="real-brave-key", gsc_site_url="sc-domain:example.com")
    assert isinstance(factory.make_competitor(settings), BraveCompetitorProvider)


@pytest.mark.parametrize("overrides", [
    {"brave_api_key": "YOUR_BRAVE_KEY_HERE", "gsc_site_url": "sc-domain:example.com"},
    {"brave_api_key": "real-brave-key", "gsc_site_url": ""},
    {},
])
def test_factory_returns_none_without_all_three_conditions(overrides):
    from aceleraseo.infrastructure.llm.factory import make_competitor

    assert make_competitor(_settings(**overrides)) is None


def test_factory_returns_none_when_google_not_connected(monkeypatch):
    from aceleraseo.infrastructure.google import oauth
    from aceleraseo.infrastructure.llm.factory import make_competitor

    monkeypatch.setattr(oauth, "load_credentials", lambda settings: None)
    settings = _settings(brave_api_key="real-brave-key", gsc_site_url="sc-domain:example.com")
    assert make_competitor(settings) is None
