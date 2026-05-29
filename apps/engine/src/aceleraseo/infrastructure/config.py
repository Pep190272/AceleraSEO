"""Typed settings loaded from environment / .env. Single source of config truth."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Read scopes only — SENSE never needs write access to Google.
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
OAUTH_SCOPES = [GSC_SCOPE, GA4_SCOPE]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    return Settings()
