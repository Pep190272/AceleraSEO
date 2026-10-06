"""SENSE use case — collect signals and persist them as time-series.

Depends only on the domain ports, so it is fully testable with fakes (no live
Google needed). Adapters are injected by the interface layer.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..domain.ports import AnalyticsProvider, RankingProvider

logger = logging.getLogger(__name__)


@dataclass
class SenseResult:
    rankings_fetched: int
    rankings_new: int
    pages_with_conversions: int
    # Rows the conversions source returned (landing pages). 0 with a source = no data.
    conversion_rows: int = 0


class CollectSignals:
    def __init__(
        self,
        rankings: RankingProvider,
        analytics: AnalyticsProvider | None,
        repository,
    ):
        self._rankings = rankings
        # None = no conversions source configured (see make_analytics).
        self._analytics = analytics
        self._repo = repository

    def execute(
        self,
        site_url: str,
        property_id: str,
        days: int = 90,
    ) -> SenseResult:
        signals = self._rankings.fetch_rankings(site_url, days)
        new_rows = self._repo.save_many(site_url, signals)

        pages_with_conversions = 0
        rows = 0
        if self._analytics is not None:
            conversions = self._analytics.fetch_conversions(property_id, days)
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
