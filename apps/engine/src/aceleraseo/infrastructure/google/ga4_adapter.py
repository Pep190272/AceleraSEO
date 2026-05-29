"""GA4 Data API adapter — implements domain.ports.AnalyticsProvider.

Pulls conversions per landing page so DECIDE can weight keywords by money,
not just traffic. Joining this with GSC rankings (by URL) is the core edge:
"this page ranks AND converts" vs "ranks but is worthless".
"""
from __future__ import annotations

from datetime import date, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials


class GA4AnalyticsProvider:
    def __init__(self, credentials: Credentials):
        self._client = BetaAnalyticsDataClient(credentials=credentials)

    def fetch_conversions(self, property_id: str, days: int) -> dict[str, float]:
        """Return {landing_page_path: conversions} for the window."""
        start = (date.today() - timedelta(days=days)).isoformat()
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start, end_date="today")],
            dimensions=[Dimension(name="landingPagePlusQueryString")],
            metrics=[Metric(name="conversions")],
        )
        resp = self._client.run_report(request)
        result: dict[str, float] = {}
        for row in resp.rows:
            path = row.dimension_values[0].value
            conversions = float(row.metric_values[0].value or 0.0)
            result[path] = conversions
        return result
