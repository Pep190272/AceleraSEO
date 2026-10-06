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
    # Rows GA4 returned (landing pages). 0 with a property set = GA4 has no data.
    ga4_rows: int = 0


class CollectSignals:
    def __init__(
        self,
        rankings: RankingProvider,
        analytics: AnalyticsProvider,
        repository,
    ):
        self._rankings = rankings
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
        ga4_rows = 0
        if property_id:
            conversions = self._analytics.fetch_conversions(property_id, days)
            pages_with_conversions = sum(1 for v in conversions.values() if v > 0)
            ga4_rows = len(conversions)
            logger.info(
                "GA4 returned %d landing pages, %.0f key events in total, %d pages with > 0",
                ga4_rows,
                sum(conversions.values()),
                pages_with_conversions,
            )
            if ga4_rows == 0:
                logger.warning(
                    "GA4 returned no rows for the last %d days: the property is receiving "
                    "no data. Check that the Google tag is installed on the site.",
                    days,
                )
        else:
            logger.info("GA4 skipped: no property id configured")

        return SenseResult(
            rankings_fetched=len(signals),
            rankings_new=new_rows,
            pages_with_conversions=pages_with_conversions,
            ga4_rows=ga4_rows,
        )
