from datetime import date

from aceleraseo.domain.learn import evaluate_outcome
from aceleraseo.domain.models import RankingSignal, Trend


def _sig(query, position, clicks=10, impressions=100, d=date(2026, 5, 1)):
    return RankingSignal(query=query, page="/p", position=position, clicks=clicks,
                         impressions=impressions, ctr=0.1, observed_on=d)


def _delta(report, query):
    return next(d for d in report.deltas if d.query == query)


def test_improved_when_position_moves_up():
    before = [_sig("seo", 8.0)]
    after = [_sig("seo", 3.0)]
    d = _delta(evaluate_outcome(before, after), "seo")
    assert d.trend is Trend.IMPROVED
    assert d.position_change == -5.0   # negative = moved up


def test_declined_when_position_drops():
    d = _delta(evaluate_outcome([_sig("seo", 3.0)], [_sig("seo", 9.0)]), "seo")
    assert d.trend is Trend.DECLINED
    assert d.position_change == 6.0


def test_stable_within_noise_band():
    d = _delta(evaluate_outcome([_sig("seo", 4.0)], [_sig("seo", 4.2)]), "seo")
    assert d.trend is Trend.STABLE


def test_new_and_lost_queries():
    report = evaluate_outcome([_sig("old", 5.0)], [_sig("fresh", 2.0)])
    assert _delta(report, "fresh").trend is Trend.NEW
    assert _delta(report, "old").trend is Trend.LOST


def test_position_is_impression_weighted():
    # Two rows for same query: a high-impression good rank should dominate.
    before = [_sig("seo", 2.0, impressions=1000), _sig("seo", 50.0, impressions=10)]
    after = [_sig("seo", 2.0, impressions=1000), _sig("seo", 50.0, impressions=10)]
    d = _delta(evaluate_outcome(before, after), "seo")
    assert d.position_before is not None and d.position_before < 5.0  # weighted toward 2.0


def test_net_clicks_change_aggregates():
    before = [_sig("a", 5.0, clicks=10), _sig("b", 5.0, clicks=20)]
    after = [_sig("a", 5.0, clicks=30), _sig("b", 5.0, clicks=20)]
    report = evaluate_outcome(before, after)
    assert report.net_clicks_change == 20  # a:+20, b:0
