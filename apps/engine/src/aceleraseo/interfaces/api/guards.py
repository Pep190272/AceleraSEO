"""Access guard for engine endpoints that change state.

Two rules, checked in order:

1. ``DEMO_MODE`` — a shared public instance never accepts writes (403).
2. ``ENGINE_API_TOKEN`` — when set, the caller must send the same value in the
   ``X-Engine-Token`` header (401 otherwise). The dashboard sends it server-side.
   When unset, writes are accepted: the default compose file publishes the engine
   on 127.0.0.1 only, so the caller is already local. Set the token whenever the
   engine is reachable from anywhere else.

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


def require_write_access(x_engine_token: str | None = Header(default=None)) -> None:
    if is_demo_mode():
        raise HTTPException(403, _DEMO_WRITE_MESSAGE)
    expected = os.environ.get("ENGINE_API_TOKEN", "")
    if expected and not secrets.compare_digest(x_engine_token or "", expected):
        raise HTTPException(401, "Missing or invalid X-Engine-Token header.")
