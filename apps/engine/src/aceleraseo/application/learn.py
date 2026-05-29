"""LEARN use case — read two windows from the store and measure what moved.

Closes the Sense->Decide->Act->Learn loop: it reads the persisted time-series
(the idempotent history built since M1) and produces an OutcomeReport that the
next DECIDE cycle can use to reweight strategy.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..domain.learn import evaluate_outcome
from ..domain.models import OutcomeReport


class MeasureOutcomes:
    def __init__(self, repository):
        self._repo = repository

    def execute(
        self,
        site_url: str,
        action_date: date,
        window_days: int = 28,
    ) -> OutcomeReport:
        """Compare the window before action_date vs the window after it."""
        before = self._repo.fetch_window(
            site_url, action_date - timedelta(days=window_days), action_date
        )
        after = self._repo.fetch_window(
            site_url, action_date, action_date + timedelta(days=window_days)
        )
        return evaluate_outcome(before, after)


def summarize(report: OutcomeReport) -> dict:
    """Compact, serialisable view of the loop's result."""
    from ..domain.models import Trend
    return {
        "improved": len(report.by_trend(Trend.IMPROVED)),
        "declined": len(report.by_trend(Trend.DECLINED)),
        "stable": len(report.by_trend(Trend.STABLE)),
        "new": len(report.by_trend(Trend.NEW)),
        "lost": len(report.by_trend(Trend.LOST)),
        "net_clicks_change": report.net_clicks_change,
    }
