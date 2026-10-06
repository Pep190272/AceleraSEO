"""ConversionRepository snapshots and RankingRepository.top_pages, on in-memory SQLite."""
from datetime import date

from aceleraseo.domain.models import ConversionCount, ConversionSnapshot, RankingSignal
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.repository import (
    ConversionRepository,
    RankingRepository,
)

DAY = date(2026, 10, 6)


def _repo() -> ConversionRepository:
    return ConversionRepository(make_session_factory("sqlite:///:memory:"))


def _rows(snapshot: ConversionSnapshot | None) -> set[tuple[str, str, int]]:
    assert snapshot is not None
    return {(r.path, r.type, r.count) for r in snapshot.rows}


def test_saving_the_same_day_twice_replaces_it():
    repo = _repo()
    first = [ConversionCount("/a/", "form", 2), ConversionCount("/b/", "form", 1)]
    assert repo.save_snapshot("site", ConversionSnapshot(DAY, 90, first)) == 2
    assert repo.save_snapshot("site", ConversionSnapshot(DAY, 90, first)) == 2
    assert _rows(repo.latest_snapshot("site")) == {("/a/", "form", 2), ("/b/", "form", 1)}

    repo.save_snapshot("site", ConversionSnapshot(DAY, 28, [ConversionCount("/a/", "form", 3)]))
    latest = repo.latest_snapshot("site")
    assert _rows(latest) == {("/a/", "form", 3)}  # /b/ dropped out, it does not linger
    assert latest is not None and latest.window_days == 28


def test_latest_snapshot_is_the_newest_window_and_per_site():
    repo = _repo()
    repo.save_snapshot("site", ConversionSnapshot(date(2026, 9, 1), 90,
                                                  [ConversionCount("/a/", "form", 9)]))
    repo.save_snapshot("site", ConversionSnapshot(DAY, 90, [ConversionCount("/a/", "form", 1)]))
    assert _rows(repo.latest_snapshot("site")) == {("/a/", "form", 1)}
    assert repo.latest_snapshot("other") is None


def test_an_empty_collection_supersedes_the_previous_one():
    repo = _repo()
    repo.save_snapshot("site", ConversionSnapshot(date(2026, 9, 1), 90,
                                                  [ConversionCount("/a/", "form", 9)]))
    assert repo.save_snapshot("site", ConversionSnapshot(DAY, 90, [])) == 0
    latest = repo.latest_snapshot("site")
    assert latest is not None and latest.window_end == DAY and latest.rows == []


def test_top_pages_picks_most_clicks_then_impressions():
    repo = RankingRepository(make_session_factory("sqlite:///:memory:"))
    repo.save_many("site", [
        RankingSignal("seo", "https://x.test/a", 3.0, 5, 50, 0.1, DAY),
        RankingSignal("seo", "https://x.test/b", 2.0, 5, 80, 0.1, DAY),
        RankingSignal("seo", "https://x.test/c", 1.0, 1, 900, 0.1, DAY),
        RankingSignal("old", "https://x.test/a", 1.0, 1, 10, 0.1, date(2026, 1, 1)),
    ])
    assert repo.top_pages("site", date(2026, 10, 1), DAY, ["seo", "old"]) == {
        "seo": "https://x.test/b"}
    assert repo.top_pages("site", date(2026, 10, 1), DAY, []) == {}
