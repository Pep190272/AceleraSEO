"""Google OAuth helper — builds the consent flow and caches/loads credentials.

Read-only scopes only (see config.OAUTH_SCOPES). The token is persisted to a
gitignored JSON file so the loop can run unattended after a one-time consent.

The consent flow spans two HTTP requests (login, then Google's callback), so the
values that must survive between them — the OAuth ``state`` and the PKCE
``code_verifier`` that google-auth-oauthlib generates — are kept in a short-lived,
single-use in-process registry. A callback whose state this engine did not issue
(or already consumed, or issued too long ago) is rejected before any token
exchange happens.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from functools import partial
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ..config import OAUTH_SCOPES, Settings

logger = logging.getLogger(__name__)

# Explicit bound on calls to Google's token endpoint (code exchange and refresh).
# Without it requests-oauthlib waits forever and google-auth waits 120 s, which
# would hang the OAuth callback or the Settings tab's status check.
GOOGLE_HTTP_TIMEOUT_SECONDS = 15.0


class InvalidStateError(Exception):
    """The callback's ``state`` was not issued by this engine, was reused, or expired."""


class PendingAuthorizations:
    """Consent flows started by this engine and not yet completed.

    Maps ``state`` -> PKCE ``code_verifier``. Entries are single-use and expire,
    and the registry is bounded so repeated login clicks cannot grow it forever.
    In-process on purpose: the engine runs as a single uvicorn worker, and a
    restart mid-consent only costs the user one more click.
    """

    def __init__(
        self,
        ttl_seconds: float = 600.0,
        max_entries: int = 32,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, state: str, code_verifier: str) -> None:
        with self._lock:
            self._entries[state] = (code_verifier, self._clock() + self._ttl)
            self._entries.move_to_end(state)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)

    def pop(self, state: str) -> str | None:
        """Consume ``state``; return its code verifier, or None if unknown/expired."""
        with self._lock:
            entry = self._entries.pop(state, None)
        if entry is None:
            return None
        code_verifier, expires_at = entry
        if self._clock() > expires_at:
            return None
        return code_verifier


_pending = PendingAuthorizations()


def _registry(pending: PendingAuthorizations | None) -> PendingAuthorizations:
    # Resolved at call time (not as a default argument) so tests can swap it.
    return pending if pending is not None else _pending


def is_configured(settings: Settings) -> bool:
    """True when the OAuth client id and secret needed to start consent are set."""
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)


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


def build_flow(
    settings: Settings, state: str | None = None, code_verifier: str | None = None
) -> Flow:
    flow = Flow.from_client_config(
        _client_config(settings),
        scopes=OAUTH_SCOPES,
        state=state,
        code_verifier=code_verifier,
    )
    flow.redirect_uri = settings.google_oauth_redirect_uri
    return flow


def authorization_url(settings: Settings, pending: PendingAuthorizations | None = None) -> str:
    flow = build_flow(settings)
    url, state = flow.authorization_url(
        access_type="offline",          # get a refresh token
        include_granted_scopes="true",
        prompt="consent",
    )
    # authorization_url() autogenerates the PKCE verifier; the callback runs on a
    # new Flow, so without remembering it the token exchange is rejected by Google.
    _registry(pending).add(state, flow.code_verifier)
    return url


def discard_state(state: str, pending: PendingAuthorizations | None = None) -> None:
    """Forget a consent flow that ended without a code (e.g. the user cancelled)."""
    _registry(pending).pop(state)


def exchange_code(
    settings: Settings, code: str, state: str, pending: PendingAuthorizations | None = None
) -> Credentials:
    code_verifier = _registry(pending).pop(state)
    if code_verifier is None:
        raise InvalidStateError("Unknown, reused or expired OAuth state.")
    flow = build_flow(settings, state=state, code_verifier=code_verifier)
    flow.fetch_token(code=code, timeout=GOOGLE_HTTP_TIMEOUT_SECONDS)
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
    if not isinstance(data, dict):
        raise ValueError("Google token file does not contain a JSON object.")
    creds = Credentials.from_authorized_user_info(data, OAUTH_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(partial(Request(), timeout=GOOGLE_HTTP_TIMEOUT_SECONDS))
        save_credentials(settings, creds)
    return creds


def is_connected(settings: Settings) -> bool:
    """True when a cached token exists and is usable (refreshing it if expired).

    Never raises: a missing, unreadable or corrupt token file, or a refresh that
    Google rejects or that cannot reach Google, all mean "not connected" — the
    remedy for each is the same, connecting again. The reason is logged.
    """
    try:
        creds = load_credentials(settings)
    except (OSError, ValueError) as exc:
        logger.warning("Google token file is unreadable or corrupt (%s).", type(exc).__name__)
        return False
    except GoogleAuthError as exc:
        logger.warning("Google token refresh failed (%s).", type(exc).__name__)
        return False
    if creds is None:
        return False
    return bool(creds.valid or creds.refresh_token)
