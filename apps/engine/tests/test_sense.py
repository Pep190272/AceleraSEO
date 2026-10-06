"""SENSE use case tested with in-memory fakes — no live Google, no network."""
import logging
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


def test_collect_logs_ga4_totals_when_property_set(caplog):
    uc, _ = _use_case([_signal()])
    with caplog.at_level(logging.INFO, logger="aceleraseo.application.sense"):
        uc.execute(site_url="site", property_id="123", days=30)
    assert "returned 2 landing pages, 5 conversions in total, 1 pages with > 0" in caplog.text
    assert "no rows" not in caplog.text


def test_collect_warns_when_ga4_returns_no_rows(caplog):
    class EmptyAnalytics:
        def fetch_conversions(self, property_id, days):
            return {}

    uc = CollectSignals(FakeRankings([_signal()]), EmptyAnalytics(),
                        RankingRepository(make_session_factory("sqlite:///:memory:")))
    with caplog.at_level(logging.INFO, logger="aceleraseo.application.sense"):
        result = uc.execute(site_url="site", property_id="123", days=30)
    assert result.conversion_rows == 0
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "Google tag" in warnings[0].getMessage()


def test_collect_skips_and_logs_without_a_conversions_source(caplog):
    uc = CollectSignals(FakeRankings([_signal()]), None,
                        RankingRepository(make_session_factory("sqlite:///:memory:")))
    with caplog.at_level(logging.INFO, logger="aceleraseo.application.sense"):
        result = uc.execute(site_url="site", property_id="", days=30)
    assert result.pages_with_conversions == 0
    assert result.conversion_rows == 0
    assert "Conversions skipped: no conversions source configured" in caplog.text
