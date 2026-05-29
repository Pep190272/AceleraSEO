from datetime import date

from aceleraseo.application.learn import MeasureOutcomes, summarize
from aceleraseo.domain.models import RankingSignal, Trend


class FakeRepo:
    """Returns canned signals per window so the use case is tested without a DB."""
    def __init__(self, before, after):
        self._before = before
        self._after = after

    def fetch_window(self, site_url, start, end):
        # action_date is the boundary; 'before' window ends at it, 'after' starts at it.
        action = date(2026, 5, 15)
        return self._before if end <= action else self._after


def _sig(query, position, clicks=10, d=date(2026, 5, 1)):
    return RankingSignal(query=query, page="/p", position=position, clicks=clicks,
                         impressions=100, ctr=0.1, observed_on=d)


def test_measure_outcomes_compares_windows():
    repo = FakeRepo(before=[_sig("seo", 9.0)], after=[_sig("seo", 4.0)])
    report = MeasureOutcomes(repo).execute("site", date(2026, 5, 15), window_days=28)
    assert report.deltas[0].trend is Trend.IMPROVED


def test_summarize_shape():
    repo = FakeRepo(before=[_sig("seo", 9.0)], after=[_sig("seo", 4.0)])
    report = MeasureOutcomes(repo).execute("site", date(2026, 5, 15))
    s = summarize(report)
    assert s["improved"] == 1
    assert set(s) == {"improved", "declined", "stable", "new", "lost", "net_clicks_change"}
