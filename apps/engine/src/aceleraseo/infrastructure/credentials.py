"""Shared "is this value real (not a placeholder)" check.

Used by both the LLM factory (to decide which adapter to instantiate) and
settings_store (to report accurate "configured" status in the Settings tab).
Living here — rather than in `llm/factory.py` — keeps settings_store from
depending on the llm subpackage and avoids an import cycle.
"""
from __future__ import annotations


def is_real_value(value: str) -> bool:
    """A configured value must be non-empty AND not a placeholder.

    The shipped .env.example uses YOUR_*_HERE placeholders for secrets. Treating
    those as real values would select a live adapter that then fails on the
    first call (LLM factory), or report "configured" in the Settings tab for a
    credential nobody actually set (settings_store). A placeholder must behave
    exactly like "not set".
    """
    if not value:
        return False
    upper = value.upper()
    return not (upper.startswith("YOUR_") or "PLACEHOLDER" in upper or value == "change-me")
