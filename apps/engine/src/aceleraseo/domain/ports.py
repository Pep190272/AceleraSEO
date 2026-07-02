"""Ports — interfaces the application depends on. Adapters live in infrastructure/."""
from __future__ import annotations

from typing import Protocol

from .models import (
    Action,
    BusinessProfile,
    CompetitorDomain,
    CrawledPage,
    Keyword,
    RankingSignal,
    ScoredKeyword,
    SeoAudit,
    SeoPage,
)


class RankingProvider(Protocol):
    """Read rankings/performance — implemented by the GSC adapter."""
    def fetch_rankings(self, site_url: str, days: int) -> list[RankingSignal]: ...


class AnalyticsProvider(Protocol):
    """Read conversions/revenue — implemented by the GA4 adapter."""
    def fetch_conversions(self, property_id: str, days: int) -> dict[str, float]: ...


class MarketProvider(Protocol):
    """Keyword volumes / difficulty / SERP — DataForSEO or SerpApi adapter."""
    def keyword_metrics(self, terms: list[str], location: str) -> list[Keyword]: ...


class PageFetcher(Protocol):
    """Fetch + parse a single URL into a CrawledPage — implemented by the crawler."""
    def fetch(self, url: str) -> CrawledPage: ...


class Indexer(Protocol):
    """Push URLs for instant indexing — IndexNow adapter (Bing/Yandex/etc, NOT Google)."""
    def submit(self, urls: list[str]) -> bool: ...


class IndexStatusReader(Protocol):
    """Read Google index status — URL Inspection adapter (read-only)."""
    def is_indexed(self, url: str) -> bool: ...


class LLMPort(Protocol):
    """Strategy narration — Anthropic / OpenAI / Ollama adapter.

    The deterministic core builds the scored keywords and actions; the LLM only
    explains and prioritises them into an executive summary. This keeps the
    numbers trustworthy and makes the LLM an enhancement, not a dependency.
    """
    def explain_strategy(
        self,
        profile: BusinessProfile,
        keywords: list[ScoredKeyword],
        actions: list[Action],
    ) -> str: ...


class KeywordDiscoverer(Protocol):
    """Generate candidate keywords for a niche from a plain business description.

    This is the "tell it your business -> it finds the words" step. The LLM
    proposes terms with rough metrics; a MarketProvider can then replace those
    estimates with real volume/difficulty.
    """
    def discover(
        self, description: str, location: str, language: str, max_keywords: int
    ) -> list[Keyword]: ...


class CompetitorProvider(Protocol):
    """Fetch competitor domains for a target domain and their ranked keywords.

    Implemented by the DataForSEO adapter. Both steps (competitors_domain/live
    and ranked_keywords/live) are encapsulated here so use-cases stay clean.
    """
    def fetch_competitors(
        self,
        target: str,
        location: str,
        language: str,
        max_competitors: int,
        max_keywords_per_competitor: int,
    ) -> list[CompetitorDomain]: ...


class CMSPort(Protocol):
    """Manage the SEO metadata of an external site via its REST API.

    Noor is the first adapter; WordPress (future) will implement the same port.
    The port is intentionally minimal — only the three operations the use-cases need.

    IMPORTANT: update_page performs a FULL REPLACE on the remote end, not a patch.
    Callers must always supply every field, even those not being edited.
    """

    def get_audit(self) -> SeoAudit:
        """Return the site-wide SEO health summary."""
        ...

    def list_pages(self) -> list[SeoPage]:
        """Return all pages managed by the CMS SEO layer."""
        ...

    def update_page(self, page: SeoPage) -> dict:
        """Create or fully-replace one page's SEO metadata.

        Returns the adapter's confirmation dict, e.g. {"action": "updated", "url_path": "/…"}.
        Raises on validation errors or auth failures.
        """
        ...

    def verify(self) -> bool:
        """Cheap connectivity + auth probe.  Returns True only when the remote is
        reachable and the API key is accepted (e.g. a light GET /api/seo/audit check).
        """
        ...
