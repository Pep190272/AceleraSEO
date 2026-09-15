"""Access guards for engine endpoints.

``require_write_access`` protects endpoints that change state. Two rules, in order:

1. ``DEMO_MODE`` — a shared public instance never accepts writes (403).
2. ``ENGINE_API_TOKEN`` — required. The caller must send the same value in the
   ``X-Engine-Token`` header (401 otherwise). The dashboard sends it server-side.
   If the engine has no token configured, guarded endpoints fail closed with a 503
   that says how to set one, and startup logs the same instruction.

``require_token`` applies only rule 2. It protects endpoints that change no state
but spend a configured provider's quota or make the engine fetch URLs; the public
demo needs those to keep working, so demo mode does not block them.

Both are read from the process environment only — never from UI overrides, so a
caller cannot switch the guard off through ``POST /settings``.
"""
from __future__ import annotations

import logging
import os
import secrets

from fastapi import Header, HTTPException

from ...infrastructure.config import is_demo_mode

logger = logging.getLogger(__name__)

MISSING_TOKEN_MESSAGE = (
    "ENGINE_API_TOKEN is not set, so this endpoint is disabled. Generate one with "
    "`python -c \"import secrets; print(secrets.token_hex(32))\"` and set it as the "
    "ENGINE_API_TOKEN environment variable for the engine and the dashboard, then "
    "restart (docker compose loads it from .env). See the README quick start."
)

_DEMO_WRITE_MESSAGE = (
    "This is a shared demo — changes are disabled. Self-host to use this action "
    "(see the README)."
)


def warn_if_token_missing() -> None:
    """Log at startup, so a missing token is visible before the first refused call."""
    if not os.environ.get("ENGINE_API_TOKEN"):
        logger.warning(MISSING_TOKEN_MESSAGE)


def require_token(x_engine_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ENGINE_API_TOKEN", "")
    if not expected:
        raise HTTPException(503, MISSING_TOKEN_MESSAGE)
    if not secrets.compare_digest(x_engine_token or "", expected):
        raise HTTPException(401, "Missing or invalid X-Engine-Token header.")


def require_write_access(x_engine_token: str | None = Header(default=None)) -> None:
    if is_demo_mode():
        raise HTTPException(403, _DEMO_WRITE_MESSAGE)
    require_token(x_engine_token)
