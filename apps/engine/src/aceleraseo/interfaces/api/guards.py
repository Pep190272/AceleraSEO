"""Access guards for engine endpoints.

``require_write_access`` protects endpoints that change state. Two rules, in order:

1. ``DEMO_MODE`` — a shared public instance never accepts writes (403).
2. ``ENGINE_API_TOKEN`` — when set, the caller must send the same value in the
   ``X-Engine-Token`` header (401 otherwise). The dashboard sends it server-side.
   When unset, writes are accepted: the default compose file publishes the engine
   on 127.0.0.1 only, so the caller is already local. Set the token whenever the
   engine is reachable from anywhere else.

``require_token`` applies only rule 2. It protects endpoints that change no state
but spend a configured provider's quota or make the engine fetch URLs; the public
demo needs those to keep working, so demo mode does not block them.

Both are read from the process environment only — never from UI overrides, so a
caller cannot switch the guard off through ``POST /settings``.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException

from ...infrastructure.config import is_demo_mode

_DEMO_WRITE_MESSAGE = (
    "This is a shared demo — changes are disabled. Self-host to use this action "
    "(see the README)."
)


def require_token(x_engine_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ENGINE_API_TOKEN", "")
    if expected and not secrets.compare_digest(x_engine_token or "", expected):
        raise HTTPException(401, "Missing or invalid X-Engine-Token header.")


def require_write_access(x_engine_token: str | None = Header(default=None)) -> None:
    if is_demo_mode():
        raise HTTPException(403, _DEMO_WRITE_MESSAGE)
    require_token(x_engine_token)
