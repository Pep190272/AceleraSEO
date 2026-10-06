"""REPORT use case — show what SENSE collected: what ranks and what is slipping.

Reads the persisted time-series, aggregates the latest window per query and
compares it with the window of equal length right before it (the same
before/after comparison LEARN uses). Positive ``position_delta`` means worse.

Queries with fewer than ``min_impressions`` impressions in the current window are
left out, and ``position_delta`` is withheld when the previous window has fewer
than that: a handful of impressions makes the average position swing wildly.

Conversions are page-level, not query-level: each row carries the conversions of its
query's top page (most clicks, then impressions, in the window) from the latest
collection, joined on the normalised path. Queries that share a top page show the
same count. ``conversions`` is None when no conversions are collected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from ..domain.models import ConversionSnapshot, QueryRanking
from ..domain.paths import normalize_path


class RankingReader(Protocol):
    def observed_range(self, site_url: str) -> tuple[date | None, date | None]: ...

    def summarize_by_query(
        self,
        site_url: str,
        start: date,
        end: date,
        limit: int | None = None,
        min_impressions: int = 0,
    ) -> list[QueryRanking]: ...

    def top_pages(
        self, site_url: str, start: date, end: date, queries: list[str]
    ) -> dict[str, str]: ...


class ConversionReader(Protocol):
    def latest_snapshot(self, site_url: str, source: str) -> ConversionSnapshot | None: ...


@dataclass(frozen=True)
class RankingRow:
    query: str
    clicks: int
    impressions: int
    position: float
    previous_position: float | None
    previous_impressions: int
    position_delta: float | None
    top_page: str | None = None
    conversions: int | None = None


@dataclass(frozen=True)
class RankingsReport:
    site_url: str
    start: date
    end: date
    days: int
    min_impressions: int
    first_observed_on: date | None
    last_observed_on: date | None
    rows: list[RankingRow] = field(default_factory=list)
    # The window of the conversions snapshot shown, or None when none is collected.
    conversions_end: date | None = None
    conversions_days: int | None = None


class ReportRankings:
    def __init__(
        self,
        repository: RankingReader,
        conversions: ConversionReader | None = None,
        conversions_source: str = "none",
    ) -> None:
        self._repo = repository
        # No reader or source "none": rows carry conversions=None.
        self._conversions = conversions if conversions_source != "none" else None
        self._source = conversions_source

    def execute(
        self,
        site_url: str,
        today: date,
        days: int = 28,
        limit: int = 50,
        min_impressions: int = 0,
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
            return RankingsReport(site_url, start, end, days, min_impressions, first, last)

        current = self._repo.summarize_by_query(site_url, start, end, limit, min_impressions)
        prev_end = start - timedelta(days=1)
        previous = {
            r.query: r
            for r in self._repo.summarize_by_query(
                site_url, prev_end - timedelta(days=days - 1), prev_end
            )
        }
        snapshot = (
            self._conversions.latest_snapshot(site_url, self._source)
            if self._conversions else None
        )
        totals = snapshot.totals() if snapshot else {}
        tops = (
            self._repo.top_pages(site_url, start, end, [r.query for r in current])
            if snapshot else {}
        )
        rows = []
        for r in current:
            top = tops.get(r.query)
            conversions: int | None = None
            if snapshot is not None:
                conversions = totals.get(normalize_path(top), 0) if top else 0
            before = previous.get(r.query)
            delta = None
            if before is not None and before.impressions >= min_impressions:
                delta = round(r.position - before.position, 2)
            rows.append(RankingRow(
                query=r.query,
                clicks=r.clicks,
                impressions=r.impressions,
                position=round(r.position, 2),
                previous_position=None if before is None else round(before.position, 2),
                previous_impressions=0 if before is None else before.impressions,
                position_delta=delta,
                top_page=top,
                conversions=conversions,
            ))
        return RankingsReport(
            site_url, start, end, days, min_impressions, first, last, rows,
            conversions_end=snapshot.window_end if snapshot else None,
            conversions_days=snapshot.window_days if snapshot else None,
        )
