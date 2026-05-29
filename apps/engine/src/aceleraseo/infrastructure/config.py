"""Typed settings loaded from environment / .env, then UI overrides.

Layering (lowest to highest precedence):
  1. defaults below
  2. environment / .env
  3. runtime overrides written by the Settings tab (settings_store)

This is what lets a self-hoster paste API keys in the UI instead of editing
.env by hand — "descomplicar lo complicado".
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Read scopes only — SENSE never needs write access to Google.
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
OAUTH_SCOPES = [GSC_SCOPE, GA4_SCOPE]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Demo mode: a public shared instance. Disables writing secrets via the UI
    # so one visitor's keys can never land in an instance others use.
    demo_mode: bool = False

    app_env: str = "development"
    app_port: int = 8000
    secret_key: str = "dev-only-change-me"
    log_level: str = "info"

    database_url: str = "sqlite:///./data/aceleraseo.db"

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    google_client_secret_file: str = "./client_secret.json"
    ga4_property_id: str = ""
    gsc_site_url: str = ""

    # Where the OAuth token is cached after the consent flow (gitignored).
    google_token_file: str = "./gsc-token.json"

    # Market data (bring-your-own-key — ADR-0001).
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    serpapi_key: str = ""

    # LLM (DECIDE narration). Falls back to NullLLM when no key is set.
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # IndexNow (ACT — instant indexing on Bing/Yandex/etc; NOT Google).
    indexnow_key: str = ""
    indexnow_key_location: str = ""

    # Autonomy guardrails (ADR-0002). Default: propose only, human approves.
    autonomy_mode: str = "none"          # none | limited | full
    max_auto_actions_per_day: int = 0


@lru_cache
def get_settings() -> Settings:
    from .settings_store import load_overrides

    overrides = load_overrides()
    # demo_mode comes only from the environment — never overridable via the UI.
    overrides.pop("demo_mode", None)
    return Settings(**overrides)


def reload_settings() -> None:
    """Drop the cache so the next get_settings() picks up new overrides."""
    get_settings.cache_clear()


def is_demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")
