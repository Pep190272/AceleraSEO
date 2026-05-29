"""SENSE use case — collect signals and persist them as time-series.

Depends only on the domain ports, so it is fully testable with fakes (no live
Google needed). Adapters are injected by the interface layer.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.ports import AnalyticsProvider, RankingProvider


@dataclass
class SenseResult:
    rankings_fetched: int
    rankings_new: int
    pages_with_conversions: int


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

        conversions: dict[str, float] = {}
        if property_id:
            conversions = self._analytics.fetch_conversions(property_id, days)

        return SenseResult(
            rankings_fetched=len(signals),
            rankings_new=new_rows,
            pages_with_conversions=sum(1 for v in conversions.values() if v > 0),
        )
