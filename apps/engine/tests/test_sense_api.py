"""HTTP surface for POST /sense/run: auth/config gating and honest failure mapping.

Google is never contacted — the ranking/analytics providers are replaced with
fakes at the app-module boundary, so no test here can make a live API call.
"""
import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httplib2
import pytest
from fastapi.testclient import TestClient
from google.api_core.exceptions import PermissionDenied, RetryError
from google.auth.exceptions import RefreshError, TransportError
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

import aceleraseo.interfaces.api.app as app_module
from aceleraseo.domain.models import RankingSignal
from aceleraseo.infrastructure.config import Settings


def _settings(tmp_path, **overrides) -> Settings:
    values = {
        "google_oauth_client_id": "client-id.apps.googleusercontent.com",
        "google_oauth_client_secret": "client-secret-value",
        "google_token_file": str(tmp_path / "gsc-token.json"),
        "gsc_site_url": "sc-domain:example.com",
        "ga4_property_id": "",
        "database_url": "sqlite:///:memory:",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    # /sense/run is a guarded write: the engine requires ENGINE_API_TOKEN.
    monkeypatch.setenv("ENGINE_API_TOKEN", "local-test-token")
    settings = _settings(tmp_path)
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    c = TestClient(app_module.app, headers={"X-Engine-Token": "local-test-token"})
    c.settings = settings
    return c


def _write_token(settings: Settings, *, expired: bool, content: str | None = None) -> None:
    if content is None:
        expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=-1 if expired else 1
        )
        content = json.dumps({
            "token": "access-token-value",
            "refresh_token": "refresh-token-value",
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "token_uri": "https://oauth2.googleapis.com/token",
            "expiry": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    Path(settings.google_token_file).write_text(content, encoding="utf-8")


class FakeRankingProvider:
    def __init__(self, credentials):
        self.credentials = credentials

    def fetch_rankings(self, site_url, days):
        return [
            RankingSignal(query="seo", page="/p", position=4.2, clicks=10,
                          impressions=100, ctr=0.1, observed_on=datetime.now().date()),
        ]


class FakeAnalyticsProvider:
    def __init__(self, credentials):
        self.credentials = credentials

    def fetch_conversions(self, property_id, days):
        return {"/p": 3.0}


@pytest.fixture
def fake_providers(monkeypatch):
    monkeypatch.setattr(app_module, "GSCRankingProvider", FakeRankingProvider)
    monkeypatch.setattr(app_module, "GA4AnalyticsProvider", FakeAnalyticsProvider)


class _FakeResp:
    def __init__(self, status: int):
        self.status = status
        self.reason = "error"


def _http_error(status: int) -> HttpError:
    return HttpError(_FakeResp(status), b'{"error": "denied"}')


def _raising_ranking_provider(status: int):
    class RaisingRankingProvider:
        def __init__(self, credentials):
            pass

        def fetch_rankings(self, site_url, days):
            raise _http_error(status)

    return RaisingRankingProvider


# ── gating ──
def test_sense_run_without_a_connection_is_401(client):
    res = client.post("/sense/run")
    assert res.status_code == 401
    assert "Visit /auth/google/login" in res.json()["detail"]


def test_sense_run_without_site_url_is_400(client, tmp_path, monkeypatch):
    unset = _settings(tmp_path, gsc_site_url="")
    monkeypatch.setattr(app_module, "get_settings", lambda: unset)
    _write_token(unset, expired=False)
    res = client.post("/sense/run")
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "GSC_SITE_URL" in detail
    assert "Settings" in detail  # points at the UI, not the .env file


def test_sense_run_is_blocked_in_demo_mode(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    res = client.post("/sense/run")
    assert res.status_code == 403
    assert "shared demo" in res.json()["detail"]


# ── honest failure mapping (no raw 500s) ──
def test_sense_run_with_a_corrupt_token_file_is_401_not_500(client):
    _write_token(client.settings, expired=False, content="{not json")
    res = client.post("/sense/run")
    assert res.status_code == 401
    assert "reconnect" in res.json()["detail"].lower()


def test_sense_run_when_refresh_is_rejected_is_401_not_500(client, monkeypatch):
    def rejected_refresh(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr(Credentials, "refresh", rejected_refresh)
    _write_token(client.settings, expired=True)
    res = client.post("/sense/run")
    assert res.status_code == 401
    assert "reconnect" in res.json()["detail"].lower()


def test_sense_run_when_refresh_cannot_reach_google_is_502_not_a_reconnect(client, monkeypatch):
    def unreachable_refresh(self, request):
        raise TransportError("Failed to resolve oauth2.googleapis.com")

    monkeypatch.setattr(Credentials, "refresh", unreachable_refresh)
    _write_token(client.settings, expired=True)
    res = client.post("/sense/run")
    assert res.status_code == 502
    assert "reconnect" not in res.json()["detail"].lower()


# ── success path ──
def test_sense_run_success_reports_counts_and_ga4_configured(client, fake_providers):
    _write_token(client.settings, expired=False)
    res = client.post("/sense/run", params={"days": 30})
    assert res.status_code == 200
    body = res.json()
    assert body["rankings_fetched"] == 1
    assert body["rankings_new"] == 1
    assert body["ga4_configured"] is False  # ga4_property_id is "" in _settings()


def test_sense_run_success_with_ga4_configured(client, tmp_path, monkeypatch, fake_providers):
    settings = _settings(tmp_path, ga4_property_id="123")
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    _write_token(settings, expired=False)
    res = client.post("/sense/run")
    assert res.status_code == 200
    body = res.json()
    assert body["ga4_configured"] is True
    assert body["pages_with_conversions"] == 1  # /p has 3.0 > 0


def test_sense_run_rejects_an_out_of_range_days(client):
    assert client.post("/sense/run", params={"days": 0}).status_code == 422
    assert client.post("/sense/run", params={"days": 9999}).status_code == 422


# ── Google API failures once collection is under way ──
@pytest.mark.parametrize(
    "google_status,expected_status",
    [(400, 400), (401, 401), (403, 401), (404, 400), (429, 429), (504, 504), (500, 502)],  # 500 = anything unrecognized
)
def test_sense_run_maps_google_api_failures_not_a_raw_500(
    client, monkeypatch, google_status, expected_status
):
    monkeypatch.setattr(app_module, "GSCRankingProvider", _raising_ranking_provider(google_status))
    monkeypatch.setattr(app_module, "GA4AnalyticsProvider", FakeAnalyticsProvider)
    _write_token(client.settings, expired=False)
    res = client.post("/sense/run")
    assert res.status_code == expected_status
    assert "detail" in res.json()  # readable message, never a raw traceback


def test_sense_run_maps_a_ga4_rejection_not_a_raw_500(client, tmp_path, monkeypatch, fake_providers):
    class RaisingAnalyticsProvider:
        def __init__(self, credentials):
            pass

        def fetch_conversions(self, property_id, days):
            raise PermissionDenied("no access to this GA4 property")

    settings = _settings(tmp_path, ga4_property_id="123")
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(app_module, "GA4AnalyticsProvider", RaisingAnalyticsProvider)
    _write_token(settings, expired=False)
    res = client.post("/sense/run")
    assert res.status_code == 401  # PermissionDenied.code == 403 -> mapped to 401
    assert "detail" in res.json()


# ── Google unreachable or too slow once collection is under way ──
@pytest.mark.parametrize(
    "exc,expected_status",
    [
        (httplib2.ServerNotFoundError("Unable to find the server at oauth2.googleapis.com"), 502),
        (socket.gaierror(11001, "getaddrinfo failed"), 502),
        (ConnectionResetError("connection reset by peer"), 502),
        (TransportError("could not reach the token endpoint"), 502),
        (TimeoutError("timed out"), 504),
        (RetryError("Timeout of 600.0s exceeded", cause=None), 504),
    ],
    ids=["dns-httplib2", "dns-socket", "connection-reset", "auth-transport", "timeout", "ga4-retry"],
)
def test_sense_run_maps_network_failures_not_a_raw_500(client, monkeypatch, exc, expected_status):
    class NetworkFailingRankingProvider:
        def __init__(self, credentials):
            pass

        def fetch_rankings(self, site_url, days):
            raise exc

    monkeypatch.setattr(app_module, "GSCRankingProvider", NetworkFailingRankingProvider)
    monkeypatch.setattr(app_module, "GA4AnalyticsProvider", FakeAnalyticsProvider)
    _write_token(client.settings, expired=False)
    res = client.post("/sense/run")
    assert res.status_code == expected_status
    assert "Google" in res.json()["detail"]
