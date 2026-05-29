"""Ports — interfaces the application depends on. Adapters live in infrastructure/."""
from __future__ import annotations

from typing import Protocol

from .models import ActionPlan, BusinessProfile, Keyword, RankingSignal


class RankingProvider(Protocol):
    """Read rankings/performance — implemented by the GSC adapter."""
    def fetch_rankings(self, site_url: str, days: int) -> list[RankingSignal]: ...


class AnalyticsProvider(Protocol):
    """Read conversions/revenue — implemented by the GA4 adapter."""
    def fetch_conversions(self, property_id: str, days: int) -> dict[str, float]: ...


class MarketProvider(Protocol):
    """Keyword volumes / difficulty / SERP — DataForSEO or SerpApi adapter."""
    def keyword_metrics(self, terms: list[str], location: str) -> list[Keyword]: ...


class Indexer(Protocol):
    """Push URLs for instant indexing — IndexNow adapter (Bing/Yandex/etc, NOT Google)."""
    def submit(self, urls: list[str]) -> bool: ...


class IndexStatusReader(Protocol):
    """Read Google index status — URL Inspection adapter (read-only)."""
    def is_indexed(self, url: str) -> bool: ...


class LLMPort(Protocol):
    """Strategy reasoning — Anthropic / OpenAI / Ollama adapter."""
    def reason_strategy(self, profile: BusinessProfile, context: str) -> ActionPlan: ...
