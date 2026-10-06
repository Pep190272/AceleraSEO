"""SENSE use case — collect signals and persist them as time-series.

Depends only on the domain ports, so it is fully testable with fakes (no live
Google needed). Adapters are injected by the interface layer.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..domain.models import ConversionCount, ConversionSnapshot, RankingSignal
from ..domain.paths import normalize_path
from ..domain.ports import AnalyticsProvider, ConversionRowsProvider, RankingProvider

# Type stored for a source that only reports per-page totals (GA4 key events).
TOTALS_ONLY_TYPE = "ga4_key_event"

logger = logging.getLogger(__name__)


@dataclass
class SenseResult:
    rankings_fetched: int
    rankings_new: int
    pages_with_conversions: int
    # Rows the conversions source returned (landing pages). 0 with a source = no data.
    conversion_rows: int = 0


class RankingWriter(Protocol):
    def save_many(self, site_url: str, signals: list[RankingSignal]) -> int: ...


class ConversionWriter(Protocol):
    def save_snapshot(self, site_url: str, snapshot: ConversionSnapshot) -> int: ...


class CollectSignals:
    def __init__(
        self,
        rankings: RankingProvider,
        analytics: AnalyticsProvider | None,
        repository: RankingWriter,
        conversions: ConversionWriter | None = None,
    ) -> None:
        self._rankings = rankings
        # None = no conversions source configured (see make_analytics).
        self._analytics = analytics
        self._repo = repository
        # None = conversions are counted but not persisted.
        self._conversions = conversions

    def execute(
        self,
        site_url: str,
        property_id: str,
        days: int = 90,
        today: date | None = None,
    ) -> SenseResult:
        signals = self._rankings.fetch_rankings(site_url, days)
        new_rows = self._repo.save_many(site_url, signals)

        pages_with_conversions = 0
        rows = 0
        if self._analytics is not None:
            snapshot = _snapshot(self._analytics, property_id, days, today or date.today())
            if self._conversions is not None:
                self._conversions.save_snapshot(site_url, snapshot)
            conversions = snapshot.totals()
            pages_with_conversions = sum(1 for v in conversions.values() if v > 0)
            rows = len(conversions)
            logger.info(
                "Conversions source returned %d landing pages, %.0f conversions in total, "
                "%d pages with > 0",
                rows,
                sum(conversions.values()),
                pages_with_conversions,
            )
            if rows == 0:
                logger.warning(
                    "The conversions source returned no rows for the last %d days. For GA4, "
                    "check that the Google tag is installed; for WordPress, that the "
                    "endpoint records conversions.",
                    days,
                )
        else:
            logger.info("Conversions skipped: no conversions source configured")

        return SenseResult(
            rankings_fetched=len(signals),
            rankings_new=new_rows,
            pages_with_conversions=pages_with_conversions,
            conversion_rows=rows,
        )


def _snapshot(
    analytics: AnalyticsProvider, property_id: str, days: int, today: date
) -> ConversionSnapshot:
    """Per-type rows when the source has them, else its per-page totals as one type."""
    if isinstance(analytics, ConversionRowsProvider):
        return analytics.fetch_conversion_rows(days)
    totals: dict[str, int] = {}
    for page, value in analytics.fetch_conversions(property_id, days).items():
        path = normalize_path(page)
        totals[path] = totals.get(path, 0) + round(value)
    rows = [ConversionCount(path, TOTALS_ONLY_TYPE, n) for path, n in totals.items()]
    return ConversionSnapshot(window_end=today, window_days=days, source="ga4", rows=rows)
