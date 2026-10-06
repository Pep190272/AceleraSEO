"""RankingRepository read-back against a real SQLite file."""
from datetime import date

from aceleraseo.domain.models import RankingSignal
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.repository import RankingRepository

SITE = "sc-domain:x.test"


def _sig(query, page, position, clicks, impressions, day):
    return RankingSignal(query=query, page=page, position=position, clicks=clicks,
                         impressions=impressions, ctr=0.0, observed_on=day)


def _repo(tmp_path):
    return RankingRepository(make_session_factory(f"sqlite:///{tmp_path}/t.db"))


def test_summarize_aggregates_per_query_with_weighted_position(tmp_path):
    repo = _repo(tmp_path)
    repo.save_many(SITE, [
        _sig("seo", "/a", 2.0, 5, 300, date(2026, 9, 1)),
        _sig("seo", "/b", 10.0, 1, 100, date(2026, 9, 2)),
        _sig("ads", "/a", 7.0, 9, 0, date(2026, 9, 2)),
        _sig("seo", "/a", 1.0, 99, 999, date(2026, 8, 1)),   # outside the window
    ])
    repo.save_many("sc-domain:other.test", [_sig("seo", "/a", 1.0, 50, 50, date(2026, 9, 1))])

    rows = repo.summarize_by_query(SITE, date(2026, 9, 1), date(2026, 9, 30))

    assert [r.query for r in rows] == ["ads", "seo"]
    ads, seo = rows
    assert (seo.clicks, seo.impressions) == (6, 400)
    assert seo.position == (2.0 * 300 + 10.0 * 100) / 400
    assert ads.position == 7.0          # no impressions: plain average
    assert repo.summarize_by_query(SITE, date(2026, 9, 1), date(2026, 9, 30), 1) == [ads]


def test_min_impressions_filters_on_summed_impressions_before_limit(tmp_path):
    repo = _repo(tmp_path)
    repo.save_many(SITE, [
        _sig("thin", "/", 1.0, 50, 4, date(2026, 9, 1)),     # most clicks, too few impressions
        _sig("split", "/a", 3.0, 2, 6, date(2026, 9, 1)),    # 6 + 6 = 12 across two rows
        _sig("split", "/b", 3.0, 2, 6, date(2026, 9, 2)),
        _sig("wide", "/", 5.0, 1, 500, date(2026, 9, 1)),
    ])
    window = (SITE, date(2026, 9, 1), date(2026, 9, 30))

    assert [r.query for r in repo.summarize_by_query(*window, 1, 10)] == ["split"]
    assert [r.query for r in repo.summarize_by_query(*window, None, 10)] == ["split", "wide"]
    assert [r.query for r in repo.summarize_by_query(*window, 1, 0)] == ["thin"]


def test_observed_range(tmp_path):
    repo = _repo(tmp_path)
    assert repo.observed_range(SITE) == (None, None)
    repo.save_many(SITE, [_sig("q", "/", 1.0, 1, 1, date(2026, 9, 3)),
                          _sig("q", "/", 1.0, 1, 1, date(2026, 9, 9))])
    assert repo.observed_range(SITE) == (date(2026, 9, 3), date(2026, 9, 9))
