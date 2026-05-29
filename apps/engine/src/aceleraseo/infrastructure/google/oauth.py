"""Google OAuth helper — builds the consent flow and caches/loads credentials.

Read-only scopes only (see config.OAUTH_SCOPES). The token is persisted to a
gitignored JSON file so the loop can run unattended after a one-time consent.
"""
from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ..config import OAUTH_SCOPES, Settings


def _client_config(settings: Settings) -> dict:
    return {
        "web": {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }


def build_flow(settings: Settings) -> Flow:
    flow = Flow.from_client_config(_client_config(settings), scopes=OAUTH_SCOPES)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    return flow


def authorization_url(settings: Settings) -> str:
    flow = build_flow(settings)
    url, _ = flow.authorization_url(
        access_type="offline",          # get a refresh token
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code(settings: Settings, code: str) -> Credentials:
    flow = build_flow(settings)
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_credentials(settings, creds)
    return creds


def save_credentials(settings: Settings, creds: Credentials) -> None:
    Path(settings.google_token_file).write_text(creds.to_json(), encoding="utf-8")


def load_credentials(settings: Settings) -> Credentials | None:
    path = Path(settings.google_token_file)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    creds = Credentials.from_authorized_user_info(data, OAUTH_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(settings, creds)
    return creds
