"""Runtime settings overrides written by the Settings tab.

Persists a small JSON file (in the data dir, gitignored) that overrides .env
values. Secret fields are never returned in clear text by the API — the schema
here marks which fields are secret so the interface can mask them.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_OVERRIDES_PATH = os.environ.get(
    "SETTINGS_OVERRIDES_FILE", "./data/settings-overrides.json"
)


@dataclass(frozen=True)
class Field:
    key: str          # matches a Settings attribute
    label: str
    group: str
    secret: bool      # masked on read; only "set/not set" exposed
    description: str
    placeholder: str = ""


# The predefined fields the UI renders. Editing this drives the Settings tab —
# add a field here and it appears in the UI automatically.
SCHEMA: list[Field] = [
    Field("gsc_site_url", "Search Console site URL", "Google", False,
          "e.g. sc-domain:example.com — the property to read rankings from.",
          "sc-domain:example.com"),
    Field("ga4_property_id", "GA4 property ID", "Google", False,
          "Numeric GA4 property id for conversions.", "123456789"),
    Field("google_oauth_client_id", "OAuth client ID", "Google", True,
          "From Google Cloud Console (Search Console + Analytics Data APIs)."),
    Field("google_oauth_client_secret", "OAuth client secret", "Google", True,
          "From Google Cloud Console."),
    Field("anthropic_api_key", "Anthropic API key", "AI strategist", True,
          "Optional — enables the LLM narrative. Without it the engine still works."),
    Field("anthropic_model", "Anthropic model", "AI strategist", False,
          "Model id for the strategy narrative.", "claude-opus-4-8"),
    Field("dataforseo_login", "DataForSEO login", "Market data", True,
          "Optional — keyword volumes & difficulty (bring-your-own-key)."),
    Field("dataforseo_password", "DataForSEO password", "Market data", True,
          "Optional — paired with the login above."),
    Field("indexnow_key", "IndexNow key", "Indexing", True,
          "Optional — instant indexing on Bing/Yandex (not Google)."),
    Field("indexnow_key_location", "IndexNow key URL", "Indexing", False,
          "Public URL hosting your IndexNow key file.",
          "https://example.com/yourkey.txt"),
    Field("autonomy_mode", "Autonomy mode", "Safety", False,
          "none = propose only (safe default) · limited · full.", "none"),
    Field("max_auto_actions_per_day", "Max auto actions/day", "Safety", False,
          "Hard cap when autonomy is not 'none'.", "0"),
]

_KEYS = {f.key for f in SCHEMA}


def load_overrides() -> dict:
    path = Path(_OVERRIDES_PATH)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    # Only accept known keys — never let the file inject arbitrary settings.
    return {k: v for k, v in data.items() if k in _KEYS}


def save_overrides(values: dict) -> None:
    current = load_overrides()
    for k, v in values.items():
        if k not in _KEYS:
            continue
        # Empty string means "clear this override" (fall back to .env/default).
        if v == "":
            current.pop(k, None)
        else:
            current[k] = v
    path = Path(_OVERRIDES_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def describe(settings) -> list[dict]:
    """Field metadata + current state. Secrets show 'set/not set', never values."""
    out: list[dict] = []
    for f in SCHEMA:
        value = getattr(settings, f.key, "")
        out.append({
            "key": f.key,
            "label": f.label,
            "group": f.group,
            "secret": f.secret,
            "description": f.description,
            "placeholder": f.placeholder,
            "is_set": bool(value) and str(value) not in ("0", "none"),
            # Non-secret values are echoed so the UI can show them; secrets are not.
            "value": "" if f.secret else str(value),
        })
    return out
