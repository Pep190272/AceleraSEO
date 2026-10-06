"""ReportRankings: window maths and deltas over a fake repository."""
from datetime import date

from aceleraseo.application.report import ReportRankings
from aceleraseo.domain.models import QueryRanking


class FakeRepo:
    def __init__(self, observed, windows):
        self._observed = observed
        self._windows = windows
        self.calls: list[tuple[date, date, int | None, int]] = []

    def observed_range(self, site_url):
        return self._observed

    def summarize_by_query(self, site_url, start, end, limit=None, min_impressions=0):
        self.calls.append((start, end, limit, min_impressions))
        return self._windows.get((start, end), [])


def test_empty_store_returns_no_rows_and_no_queries():
    repo = FakeRepo((None, None), {})
    report = ReportRankings(repo).execute("sc-domain:x.test", date(2026, 10, 5), 7, 50)
    assert report.rows == []
    assert report.first_observed_on is None and report.last_observed_on is None
    assert (report.start, report.end) == (date(2026, 9, 29), date(2026, 10, 5))
    assert repo.calls == []


def test_window_ends_at_last_observed_day_and_compares_previous_window():
    current = (date(2026, 9, 24), date(2026, 9, 30))
    previous = (date(2026, 9, 17), date(2026, 9, 23))
    repo = FakeRepo((date(2026, 8, 1), date(2026, 9, 30)), {
        current: [QueryRanking("seo", 10, 100, 4.0), QueryRanking("new", 1, 5, 9.0)],
        previous: [QueryRanking("seo", 8, 90, 6.5)],
    })
    report = ReportRankings(repo).execute("sc-domain:x.test", date(2026, 10, 5), 7, 20)

    assert (report.start, report.end) == current
    assert repo.calls == [(*current, 20, 0), (*previous, None, 0)]
    seo, new = report.rows
    assert (seo.previous_position, seo.position_delta) == (6.5, -2.5)
    assert (new.previous_position, new.position_delta) == (None, None)
    assert (seo.previous_impressions, new.previous_impressions) == (90, 0)


def test_window_never_ends_after_today():
    repo = FakeRepo((date(2026, 10, 1), date(2026, 10, 9)), {})
    report = ReportRankings(repo).execute("sc-domain:x.test", date(2026, 10, 5), 1, 50)
    assert (report.start, report.end) == (date(2026, 10, 5), date(2026, 10, 5))
    assert report.rows == []


def test_delta_is_withheld_when_the_previous_window_is_too_thin():
    current = (date(2026, 9, 24), date(2026, 9, 30))
    previous = (date(2026, 9, 17), date(2026, 9, 23))
    repo = FakeRepo((date(2026, 8, 1), date(2026, 9, 30)), {
        current: [QueryRanking("seo", 10, 100, 4.0), QueryRanking("blip", 3, 40, 2.0)],
        previous: [QueryRanking("seo", 8, 90, 6.5), QueryRanking("blip", 0, 2, 81.5)],
    })
    report = ReportRankings(repo).execute("sc-domain:x.test", date(2026, 10, 5), 7, 20, 10)

    assert report.min_impressions == 10
    # The current window is filtered in the repository; the previous one is not,
    # so a thin previous window is still reported, just not compared.
    assert repo.calls == [(*current, 20, 10), (*previous, None, 0)]
    seo, blip = report.rows
    assert (seo.previous_impressions, seo.position_delta) == (90, -2.5)
    assert (blip.previous_impressions, blip.previous_position, blip.position_delta) == (
        2, 81.5, None)
