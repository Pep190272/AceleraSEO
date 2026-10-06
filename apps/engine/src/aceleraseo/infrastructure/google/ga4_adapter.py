"""GA4 Data API adapter — implements domain.ports.AnalyticsProvider.

Pulls key events (formerly "conversions") per landing page so DECIDE can weight
keywords by money, not just traffic. Joining this with GSC rankings (by URL) is the core edge:
"this page ranks AND converts" vs "ranks but is worthless".
"""
from __future__ import annotations

from datetime import date, timedelta

from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from google.api_core.retry import Retry, if_exception_type
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials

# Upper bound for one runReport attempt; without it a stalled request hangs SENSE.
GA4_REPORT_TIMEOUT_SECONDS = 30.0

# Back off on quota (429) and transient 503s within a bounded budget. When the
# budget runs out, RetryError surfaces; interfaces/api/app.py maps it (and any
# other GoogleAPICallError) to a readable HTTP status instead of a raw 500.
GA4_REPORT_RETRY = Retry(
    predicate=if_exception_type(ResourceExhausted, ServiceUnavailable),
    initial=1.0,
    maximum=10.0,
    multiplier=2.0,
    timeout=60.0,
)


class GA4AnalyticsProvider:
    def __init__(self, credentials: Credentials):
        self._client = BetaAnalyticsDataClient(credentials=credentials)

    def fetch_conversions(self, property_id: str, days: int) -> dict[str, float]:
        """Return {landing_page_path: key events} for the window."""
        start = (date.today() - timedelta(days=days)).isoformat()
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start, end_date="today")],
            dimensions=[Dimension(name="landingPagePlusQueryString")],
            # "conversions" is the deprecated alias (2024-05-06) of "keyEvents"; same values.
            metrics=[Metric(name="keyEvents")],
        )
        resp = self._client.run_report(
            request, retry=GA4_REPORT_RETRY, timeout=GA4_REPORT_TIMEOUT_SECONDS
        )
        result: dict[str, float] = {}
        for row in resp.rows:
            path = row.dimension_values[0].value
            conversions = float(row.metric_values[0].value or 0.0)
            result[path] = conversions
        return result
