"""Redact secrets from query strings before uvicorn writes its access log.

Google's OAuth callback arrives as ``/auth/google/callback?state=...&code=...``;
uvicorn would otherwise log the one-time authorization code and the state verbatim.
"""
from __future__ import annotations

import logging
import re

ACCESS_LOGGER = "uvicorn.access"
REDACTED = "[redacted]"

# code, state, and names whose last segment is token/key/secret/password
# (access_token, api_key, client_secret, apikey) -- but not "keyword".
_SENSITIVE = re.compile(
    r"(?i)([?&](?:code|state|(?:[^=&#]*[_-])?(?:token|api_?key|key|secret|password))=)[^&#]*"
)


def redact_query(path: str) -> str:
    """Replace sensitive query values in ``path``, keeping the path and param names."""
    if "?" not in path:
        return path
    return _SENSITIVE.sub(rf"\1{REDACTED}", path)


class RedactQueryFilter(logging.Filter):
    """Rewrites uvicorn access records: args are (client, method, full_path, http, status)."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = (*args[:2], redact_query(args[2]), *args[3:])
        return True


def install_access_log_redaction() -> None:
    """Attach the filter to uvicorn's access logger once; safe to call repeatedly."""
    access = logging.getLogger(ACCESS_LOGGER)
    if not any(isinstance(f, RedactQueryFilter) for f in access.filters):
        access.addFilter(RedactQueryFilter())
