"""GA4 adapter tested with a fake Data API client — no live Google, no network."""
from types import SimpleNamespace

from google.api_core.exceptions import PermissionDenied, ResourceExhausted, ServiceUnavailable

from aceleraseo.infrastructure.google import ga4_adapter
from aceleraseo.infrastructure.google.ga4_adapter import GA4AnalyticsProvider


class FakeDataClient:
    def __init__(self, credentials):
        self.requests = []
        self.timeouts = []
        self.retries = []

    def run_report(self, request, retry=None, timeout=None):
        self.requests.append(request)
        self.timeouts.append(timeout)
        self.retries.append(retry)
        row = SimpleNamespace(
            dimension_values=[SimpleNamespace(value="/pricing")],
            metric_values=[SimpleNamespace(value="4")],
        )
        return SimpleNamespace(rows=[row])


def test_fetch_conversions_requests_key_events_per_landing_page(monkeypatch):
    monkeypatch.setattr(ga4_adapter, "BetaAnalyticsDataClient", FakeDataClient)
    provider = GA4AnalyticsProvider(credentials=None)

    result = provider.fetch_conversions("123", days=30)

    client = provider._client
    request = client.requests[0]
    assert [m.name for m in request.metrics] == ["keyEvents"]
    assert [d.name for d in request.dimensions] == ["landingPagePlusQueryString"]
    assert request.property == "properties/123"
    assert client.timeouts[0] == ga4_adapter.GA4_REPORT_TIMEOUT_SECONDS
    assert client.retries[0] is ga4_adapter.GA4_REPORT_RETRY
    assert result == {"/pricing": 4.0}


def test_report_retry_backs_off_on_quota_and_unavailable_only():
    predicate = ga4_adapter.GA4_REPORT_RETRY._predicate
    assert predicate(ResourceExhausted("quota"))
    assert predicate(ServiceUnavailable("busy"))
    assert not predicate(PermissionDenied("no access"))
