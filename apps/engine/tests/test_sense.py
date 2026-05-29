"""SENSE use case tested with in-memory fakes — no live Google, no network."""
from datetime import date

from aceleraseo.application.sense import CollectSignals
from aceleraseo.domain.models import RankingSignal
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.repository import RankingRepository


class FakeRankings:
    def __init__(self, signals):
        self._signals = signals

    def fetch_rankings(self, site_url, days):
        return self._signals


class FakeAnalytics:
    def fetch_conversions(self, property_id, days):
        return {"/pricing": 5.0, "/blog/x": 0.0}


def _signal(query="seo", page="/p", d=date(2026, 5, 1)):
    return RankingSignal(query=query, page=page, position=4.2, clicks=10,
                         impressions=100, ctr=0.1, observed_on=d)


def _use_case(signals):
    factory = make_session_factory("sqlite:///:memory:")
    return CollectSignals(FakeRankings(signals), FakeAnalytics(),
                          RankingRepository(factory)), factory


def test_collect_persists_signals_and_counts_conversions():
    uc, _ = _use_case([_signal(), _signal(query="local seo", page="/svc")])
    result = uc.execute(site_url="sc-domain:example.com", property_id="123", days=90)
    assert result.rankings_fetched == 2
    assert result.rankings_new == 2
    assert result.pages_with_conversions == 1  # only /pricing has > 0


def test_save_is_idempotent_across_cycles():
    sig = _signal()
    factory = make_session_factory("sqlite:///:memory:")
    repo = RankingRepository(factory)
    assert repo.save_many("site", [sig]) == 1
    assert repo.save_many("site", [sig]) == 0  # same tuple -> no duplicate


def test_no_conversions_when_property_missing():
    uc, _ = _use_case([_signal()])
    result = uc.execute(site_url="site", property_id="", days=30)
    assert result.pages_with_conversions == 0
