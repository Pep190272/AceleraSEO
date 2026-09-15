"""Brave Search competitor adapter — implements domain.ports.CompetitorProvider.

Free alternative to DataForSEO (ADR-0001): "GSC queries x Brave Search". Seed
queries are the target's own top GSC queries by impressions (last
_GSC_LOOKBACK_DAYS days, own verified property only — else ValueError); one
Brave Web Search call per seed query; results are aggregated in memory only
(never persisted/cached/logged — Brave forbids storing results without a
storage-rights plan) into common_keywords/avg_position/ranked_keywords per
competitor domain. organic_traffic and search_volume are always 0 (not a
defensible estimate from GSC impressions). Full rationale, quota, and ToS
citation: docs/API-LIMITS.md.

`location` is a free-text name (DataForSEO's location_name convention), not
Brave's ISO 3166-1 `country` code, so it is intentionally not forwarded; only
`language` maps trivially to Brave's `search_lang`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ValidationError

from ...domain.models import CompetitorDomain, RankedKeyword, RankingSignal
from ...domain.ports import RankingProvider

logger = logging.getLogger(__name__)

_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_RESULTS_PER_QUERY = 20

# Cost-control: Brave's free tier is $5/month at $5 per 1,000 requests, so one
# call per seed query keeps a single analysis well inside the free credit.
_SEED_QUERY_COUNT = 10
# Public (no leading underscore) — interfaces/api/app.py quotes it in the
# "brave+gsc" response notes so the message can't drift from the real window.
GSC_LOOKBACK_DAYS = 90


class BraveSearchError(RuntimeError):
    """Raised when the Brave Search API returns an error response, or is unreachable."""


class _BraveResultItem(BaseModel):
    url: str = ""


class _BraveWebSection(BaseModel):
    results: list[_BraveResultItem] = []


class _BraveResponse(BaseModel):
    """Minimal shape validation for the Brave response — enough to reject a
    malformed body as a clear BraveSearchError instead of a raw 500."""
    web: _BraveWebSection = _BraveWebSection()


def _normalize_domain(raw: str) -> str:
    """Return a bare, lowercase host with no scheme, path, port or 'www.' prefix.

    Also strips the Search Console 'sc-domain:' domain-property prefix so a
    configured gsc_site_url of either shape compares equal to a bare target
    domain like 'example.com'.
    """
    value = raw.strip()
    if value.lower().startswith("sc-domain:"):
        value = value[len("sc-domain:"):]
    if "//" not in value:
        value = f"//{value}"
    parsed = urlparse(value)
    host = (parsed.netloc or parsed.path or "").split("/")[0].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _top_queries_by_impressions(signals: list[RankingSignal], n: int) -> list[str]:
    """Distinct queries sorted by total impressions across *signals*, top *n*."""
    totals: dict[str, int] = {}
    order: list[str] = []
    for signal in signals:
        if signal.query not in totals:
            order.append(signal.query)
        totals[signal.query] = totals.get(signal.query, 0) + signal.impressions
    ranked = sorted(order, key=lambda q: totals[q], reverse=True)
    return ranked[:n]


def _extract_hosts(data: dict) -> list[str]:
    """Brave web-results -> ordered list of normalised hosts (1-based rank = index+1).

    Only the host is kept; titles/snippets are discarded immediately (never
    stored) per Brave's no-storage-without-a-plan clause.
    """
    results = ((data or {}).get("web") or {}).get("results") or []
    hosts: list[str] = []
    for item in results:
        url = item.get("url") or ""
        if not url:
            continue
        hosts.append(_normalize_domain(url))
    return hosts


@dataclass
class _Aggregate:
    """Running per-competitor-domain aggregate — in-memory only, discarded per request."""
    hits: list[tuple[str, int]] = field(default_factory=list)  # (query, brave_rank)

    def add(self, query: str, rank: int) -> None:
        self.hits.append((query, rank))

    @property
    def common_keywords(self) -> int:
        return len(self.hits)

    @property
    def avg_position(self) -> float | None:
        if not self.hits:
            return None
        return sum(rank for _, rank in self.hits) / len(self.hits)

    def ranked_keywords(self, limit: int) -> tuple[RankedKeyword, ...]:
        return tuple(
            RankedKeyword(term=query, position=float(rank), search_volume=0)
            for query, rank in self.hits[:limit]
        )


class BraveCompetitorProvider:
    """CompetitorProvider backed by the site's own GSC queries + Brave Web Search.

    See module docstring for the full design, budget, and storage constraints.
    """

    def __init__(
        self,
        api_key: str,
        gsc_provider: RankingProvider,
        gsc_site_url: str,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._gsc = gsc_provider
        self._gsc_site_url = gsc_site_url
        self._timeout = timeout

    def fetch_competitors(
        self,
        target: str,
        location: str,
        language: str,
        max_competitors: int,
        max_keywords_per_competitor: int,
    ) -> list[CompetitorDomain]:
        target_domain = _normalize_domain(target)
        if target_domain != _normalize_domain(self._gsc_site_url):
            raise ValueError(
                "Competitors via Brave only work for your own connected Search Console "
                f"site ({self._gsc_site_url}). '{target}' is a different domain."
            )

        signals = self._gsc.fetch_rankings(self._gsc_site_url, days=GSC_LOOKBACK_DAYS)
        seed_queries = _top_queries_by_impressions(signals, _SEED_QUERY_COUNT)
        if not seed_queries:
            return []

        aggregates: dict[str, _Aggregate] = {}
        for query in seed_queries:
            seen_this_query: set[str] = set()
            for rank, host in enumerate(self._brave_search(query, location, language), start=1):
                # Brave can return several results from the same domain for one
                # query — count the domain once per query, at its best (first) rank.
                if host == target_domain or host in seen_this_query:
                    continue
                seen_this_query.add(host)
                aggregates.setdefault(host, _Aggregate()).add(query, rank)

        competitors = [
            CompetitorDomain(
                domain=host,
                common_keywords=agg.common_keywords,
                avg_position=agg.avg_position,
                organic_traffic=0,
                ranked_keywords=agg.ranked_keywords(max_keywords_per_competitor),
            )
            for host, agg in aggregates.items()
        ]
        competitors.sort(
            key=lambda c: (-c.common_keywords, c.avg_position if c.avg_position is not None else float("inf"))
        )
        return competitors[:max_competitors]

    def _brave_search(self, query: str, location: str, language: str) -> list[str]:
        params: dict[str, str | int] = {"q": query, "count": _RESULTS_PER_QUERY}
        if language:
            params["search_lang"] = language
        headers = {"X-Subscription-Token": self._api_key, "Accept": "application/json"}

        try:
            resp = httpx.get(_BRAVE_ENDPOINT, params=params, headers=headers, timeout=self._timeout)
        except httpx.RequestError as exc:
            logger.warning("Brave Search request failed (%s).", type(exc).__name__)
            raise BraveSearchError("Could not reach the Brave Search API.") from exc

        if resp.status_code == 401:
            logger.warning("Brave Search returned 401.")
            raise BraveSearchError(
                "Brave API key was rejected (HTTP 401). Check it in Settings -> Market data."
            )
        if resp.status_code == 429:
            logger.warning("Brave Search returned 429.")
            raise BraveSearchError(
                "Brave Search rate limit reached (HTTP 429). Try again later, or check your "
                "monthly free credit usage."
            )
        if resp.status_code >= 400:
            logger.warning("Brave Search returned HTTP %s.", resp.status_code)
            raise BraveSearchError(f"Brave Search returned HTTP {resp.status_code}.")

        try:
            data = resp.json()
        except Exception as exc:
            raise BraveSearchError("Brave Search returned a non-JSON response.") from exc

        try:
            _BraveResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning("Brave Search returned an unexpected response shape.")
            raise BraveSearchError("Brave Search returned an unexpected response shape.") from exc

        return _extract_hosts(data)
