"""Google OAuth: consent round-trip, state/PKCE handling and the status endpoint.

Google is never contacted: the token endpoint is replaced at the
requests-oauthlib session boundary, so the real Flow code (including how it
forwards the PKCE code_verifier) still runs.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from requests_oauthlib import OAuth2Session

import aceleraseo.interfaces.api.app as app_module
from aceleraseo.infrastructure.config import Settings
from aceleraseo.infrastructure.google import oauth

DASHBOARD = "http://dash.test"


def _settings(tmp_path, **overrides) -> Settings:
    values = {
        "google_oauth_client_id": "client-id.apps.googleusercontent.com",
        "google_oauth_client_secret": "client-secret-value",
        "google_oauth_redirect_uri": "http://engine.test/auth/google/callback",
        "google_token_file": str(tmp_path / "gsc-token.json"),
        "dashboard_url": DASHBOARD,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def pending(monkeypatch):
    registry = oauth.PendingAuthorizations()
    monkeypatch.setattr(oauth, "_pending", registry)
    return registry


@pytest.fixture
def token_endpoint(monkeypatch):
    """Fake Google token endpoint; records what the exchange sent."""
    calls: list[dict] = []

    def fake_fetch_token(self, token_url, **kwargs):
        calls.append({"token_url": token_url, **kwargs})
        self.token = {
            "access_token": "access-token-value",
            "refresh_token": "refresh-token-value",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": time.time() + 3600,  # added by oauthlib when parsing a real reply
        }
        return self.token

    monkeypatch.setattr(OAuth2Session, "fetch_token", fake_fetch_token)
    return calls


@pytest.fixture
def client(tmp_path, monkeypatch, pending):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    settings = _settings(tmp_path)
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    c = TestClient(app_module.app, follow_redirects=False)
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


def _query(location: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


# ── PendingAuthorizations ────────────────────────────────────


def test_pending_state_is_single_use():
    registry = oauth.PendingAuthorizations()
    registry.add("s1", "verifier-1")
    assert registry.pop("s1") == "verifier-1"
    assert registry.pop("s1") is None


def test_pending_state_unknown_is_rejected():
    assert oauth.PendingAuthorizations().pop("never-issued") is None


def test_pending_state_expires():
    now = [1000.0]
    registry = oauth.PendingAuthorizations(ttl_seconds=60, clock=lambda: now[0])
    registry.add("s1", "verifier-1")
    now[0] += 61
    assert registry.pop("s1") is None


def test_pending_registry_is_bounded():
    registry = oauth.PendingAuthorizations(max_entries=2)
    registry.add("s1", "v1")
    registry.add("s2", "v2")
    registry.add("s3", "v3")
    assert registry.pop("s1") is None
    assert registry.pop("s3") == "v3"


# ── authorization_url / exchange_code ────────────────────────


def test_authorization_url_uses_pkce_and_remembers_the_verifier(tmp_path, pending):
    url = oauth.authorization_url(_settings(tmp_path))
    params = _query(url)
    assert params["code_challenge_method"] == "S256"
    assert params["access_type"] == "offline"
    assert pending.pop(params["state"])  # the verifier was stored under that state


def test_exchange_sends_the_verifier_from_the_login_request(tmp_path, pending, token_endpoint):
    settings = _settings(tmp_path)
    state = _query(oauth.authorization_url(settings))["state"]
    verifier = pending._entries[state][0]

    creds = oauth.exchange_code(settings, "auth-code", state)

    assert token_endpoint[0]["code"] == "auth-code"
    assert token_endpoint[0]["code_verifier"] == verifier
    assert token_endpoint[0]["timeout"] == oauth.GOOGLE_HTTP_TIMEOUT_SECONDS
    assert creds.refresh_token == "refresh-token-value"
    saved = json.loads(Path(settings.google_token_file).read_text(encoding="utf-8"))
    assert saved["refresh_token"] == "refresh-token-value"


def test_exchange_rejects_an_unknown_state_without_calling_google(
    tmp_path, pending, token_endpoint
):
    with pytest.raises(oauth.InvalidStateError):
        oauth.exchange_code(_settings(tmp_path), "auth-code", "forged-state")
    assert token_endpoint == []


def test_exchange_rejects_a_replayed_state(tmp_path, pending, token_endpoint):
    settings = _settings(tmp_path)
    state = _query(oauth.authorization_url(settings))["state"]
    oauth.exchange_code(settings, "auth-code", state)
    with pytest.raises(oauth.InvalidStateError):
        oauth.exchange_code(settings, "auth-code", state)
    assert len(token_endpoint) == 1


# ── /auth/google/login + /auth/google/callback ───────────────


def test_consent_round_trip_lands_on_dashboard_settings(client, token_endpoint):
    login = client.get("/auth/google/login")
    assert login.status_code in (302, 307)
    assert login.headers["location"].startswith("https://accounts.google.com/")
    state = _query(login.headers["location"])["state"]

    callback = client.get("/auth/google/callback", params={"code": "auth-code", "state": state})

    assert callback.status_code == 303
    location = callback.headers["location"]
    assert location.startswith(f"{DASHBOARD}/?")
    assert _query(location) == {"tab": "settings", "google": "connected"}
    assert client.get("/auth/google/status").json() == {"configured": True, "connected": True}


def test_callback_with_forged_state_redirects_with_error(client, token_endpoint):
    res = client.get("/auth/google/callback", params={"code": "auth-code", "state": "forged"})
    assert res.status_code == 303
    assert _query(res.headers["location"]) == {
        "tab": "settings", "google": "error", "reason": "state",
    }
    assert token_endpoint == []


def test_callback_when_user_cancels_redirects_with_denied(client, pending):
    state = _query(client.get("/auth/google/login").headers["location"])["state"]
    res = client.get("/auth/google/callback", params={"error": "access_denied", "state": state})
    assert _query(res.headers["location"])["reason"] == "denied"
    assert pending.pop(state) is None  # the abandoned flow is forgotten


def test_callback_without_code_redirects_with_invalid_request(client):
    res = client.get("/auth/google/callback")
    assert res.status_code == 303
    assert _query(res.headers["location"])["reason"] == "invalid_request"


def test_callback_when_token_exchange_fails_redirects_with_error(client, monkeypatch):
    def failing_fetch_token(self, token_url, **kwargs):
        raise RuntimeError("invalid_grant")

    monkeypatch.setattr(OAuth2Session, "fetch_token", failing_fetch_token)
    state = _query(client.get("/auth/google/login").headers["location"])["state"]
    res = client.get("/auth/google/callback", params={"code": "bad", "state": state})
    assert res.status_code == 303
    assert _query(res.headers["location"])["reason"] == "exchange"


def test_login_without_client_credentials_is_a_clear_400(client, tmp_path, monkeypatch):
    unconfigured = _settings(tmp_path, google_oauth_client_id="", google_oauth_client_secret="")
    monkeypatch.setattr(app_module, "get_settings", lambda: unconfigured)
    res = client.get("/auth/google/login")
    assert res.status_code == 400
    assert "client ID and secret" in res.json()["detail"]


def test_demo_mode_blocks_login_and_callback(client, monkeypatch, token_endpoint):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get("/auth/google/login").status_code == 403
    res = client.get("/auth/google/callback", params={"code": "c", "state": "s"})
    assert _query(res.headers["location"])["reason"] == "demo"
    assert token_endpoint == []


# ── /auth/google/status ──────────────────────────────────────


def test_status_unconfigured_and_no_token(client, tmp_path, monkeypatch):
    unconfigured = _settings(tmp_path, google_oauth_client_id="", google_oauth_client_secret="")
    monkeypatch.setattr(app_module, "get_settings", lambda: unconfigured)
    assert client.get("/auth/google/status").json() == {"configured": False, "connected": False}


def test_status_configured_but_not_connected(client):
    assert client.get("/auth/google/status").json() == {"configured": True, "connected": False}


def test_status_connected_with_a_valid_token_never_leaks_it(client):
    _write_token(client.settings, expired=False)
    res = client.get("/auth/google/status")
    assert res.json() == {"configured": True, "connected": True}
    for secret in ("access-token-value", "refresh-token-value", "client-secret-value",
                   "client-id.apps"):
        assert secret not in res.text


@pytest.mark.parametrize("content", ["{not json", "[]", "{}", ""])
def test_status_with_a_corrupt_token_file_is_not_connected(client, content):
    _write_token(client.settings, expired=False, content=content)
    res = client.get("/auth/google/status")
    assert res.status_code == 200
    assert res.json() == {"configured": True, "connected": False}


def test_status_when_refresh_is_rejected_is_not_connected(client, monkeypatch):
    seen_timeouts = []

    def rejected_refresh(self, request):
        seen_timeouts.append(request.keywords.get("timeout"))
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr(Credentials, "refresh", rejected_refresh)
    _write_token(client.settings, expired=True)
    res = client.get("/auth/google/status")
    assert res.status_code == 200
    assert res.json() == {"configured": True, "connected": False}
    assert seen_timeouts == [oauth.GOOGLE_HTTP_TIMEOUT_SECONDS]  # refresh is bounded


def test_status_refreshes_an_expired_token_and_reports_connected(client, monkeypatch):
    def successful_refresh(self, request):
        self.token = "new-access-token"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr(Credentials, "refresh", successful_refresh)
    _write_token(client.settings, expired=True)
    assert client.get("/auth/google/status").json() == {"configured": True, "connected": True}
