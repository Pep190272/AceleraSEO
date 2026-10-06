"""REPORT use case — show what SENSE collected: what ranks and what is slipping.

Reads the persisted time-series, aggregates the latest window per query and
compares it with the window of equal length right before it (the same
before/after comparison LEARN uses). Positive ``position_delta`` means worse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from ..domain.models import QueryRanking


class RankingReader(Protocol):
    def observed_range(self, site_url: str) -> tuple[date | None, date | None]: ...

    def summarize_by_query(
        self, site_url: str, start: date, end: date, limit: int | None = None
    ) -> list[QueryRanking]: ...


@dataclass(frozen=True)
class RankingRow:
    query: str
    clicks: int
    impressions: int
    position: float
    previous_position: float | None
    position_delta: float | None


@dataclass(frozen=True)
class RankingsReport:
    site_url: str
    start: date
    end: date
    days: int
    first_observed_on: date | None
    last_observed_on: date | None
    rows: list[RankingRow] = field(default_factory=list)


class ReportRankings:
    def __init__(self, repository: RankingReader) -> None:
        self._repo = repository

    def execute(
        self, site_url: str, today: date, days: int = 28, limit: int = 50
    ) -> RankingsReport:
        """Aggregate the last ``days`` days of data, ending at the latest collected day.

        Search Console lags a few days and collections are manual, so the window
        ends at the last observed day (never after ``today``) rather than at
        ``today``; otherwise a stale collection would read as an empty window.
        """
        first, last = self._repo.observed_range(site_url)
        end = min(last, today) if last else today
        start = end - timedelta(days=days - 1)
        if last is None:
            return RankingsReport(site_url, start, end, days, first, last)

        current = self._repo.summarize_by_query(site_url, start, end, limit)
        prev_end = start - timedelta(days=1)
        previous = {
            r.query: r.position
            for r in self._repo.summarize_by_query(
                site_url, prev_end - timedelta(days=days - 1), prev_end
            )
        }
        rows = []
        for r in current:
            before = previous.get(r.query)
            rows.append(RankingRow(
                query=r.query,
                clicks=r.clicks,
                impressions=r.impressions,
                position=round(r.position, 2),
                previous_position=None if before is None else round(before, 2),
                position_delta=None if before is None else round(r.position - before, 2),
            ))
        return RankingsReport(site_url, start, end, days, first, last, rows)
