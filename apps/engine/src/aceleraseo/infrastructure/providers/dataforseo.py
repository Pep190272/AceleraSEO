"""DataForSEO market-data adapter — implements domain.ports.MarketProvider and
domain.ports.CompetitorProvider.

Bring-your-own-key (ADR-0001): we orchestrate a third-party API, we do not own a
keyword index. The response parsers are separated as pure functions so they are
unit-testable without network or credentials.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from ...domain.models import CompetitorDomain, Keyword, RankedKeyword

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live"

# ── private numeric helpers ───────────────────────────────────────────────────

def _safe_int(value: object, default: int = 0) -> int:
    """Convert *value* to int without raising on None, "", or non-numeric strings."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert *value* to float without raising on None, "", or non-numeric strings."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _bare_host(raw: str) -> str:
    """Return only the host portion of *raw*, stripping scheme and path.

    If *raw* is already a bare host (no scheme) urlparse returns it as the
    path component; we handle that by falling back to the original string.
    """
    parsed = urlparse(raw)
    return parsed.netloc or raw
_COMPETITORS_ENDPOINT = "https://api.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live"
_RANKED_KEYWORDS_ENDPOINT = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"

# Cost-control defaults: N+1 API calls scale fast — keep them bounded.
DEFAULT_MAX_COMPETITORS = 5
DEFAULT_MAX_KEYWORDS_PER_COMPETITOR = 10


class DataForSEOMarketProvider:
    def __init__(self, login: str, password: str, timeout: float = 30.0):
        self._auth = (login, password)
        self._timeout = timeout

    def keyword_metrics(self, terms: list[str], location: str) -> list[Keyword]:
        payload = [{"keywords": terms, "location_name": location, "language_code": "es"}]
        resp = httpx.post(_ENDPOINT, auth=self._auth, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        return parse_keyword_response(resp.json())

    def fetch_competitors(
        self,
        target: str,
        location: str,
        language: str,
        max_competitors: int = DEFAULT_MAX_COMPETITORS,
        max_keywords_per_competitor: int = DEFAULT_MAX_KEYWORDS_PER_COMPETITOR,
    ) -> list[CompetitorDomain]:
        """Return up to max_competitors domains with their top ranked keywords.

        N+1 pattern: one competitors_domain/live call to get domains, then one
        ranked_keywords/live call per competitor. If a ranked_keywords call fails
        for a competitor, that competitor is still returned without keywords
        (graceful degradation) rather than aborting the whole request.
        """
        # Step 1: fetch competitor domains
        comp_payload = [{
            "target": target,
            "location_name": location,
            "language_code": language,
            "limit": max_competitors,
        }]
        comp_resp = httpx.post(
            _COMPETITORS_ENDPOINT, auth=self._auth, json=comp_payload, timeout=self._timeout
        )
        comp_resp.raise_for_status()
        competitors = parse_competitors_response(comp_resp.json())

        # Step 2: enrich each competitor with their ranked keywords (graceful degradation)
        enriched: list[CompetitorDomain] = []
        for comp in competitors:
            try:
                kw_payload = [{
                    "target": comp.domain,
                    "location_name": location,
                    "language_code": language,
                    "limit": max_keywords_per_competitor,
                }]
                kw_resp = httpx.post(
                    _RANKED_KEYWORDS_ENDPOINT,
                    auth=self._auth,
                    json=kw_payload,
                    timeout=self._timeout,
                )
                kw_resp.raise_for_status()
                ranked = parse_ranked_keywords_response(kw_resp.json())
            except Exception:
                logger.warning(
                    "ranked_keywords call failed for %s — showing competitor without keywords",
                    comp.domain,
                )
                ranked = ()

            if ranked:
                avg_position: float | None = sum(kw.position for kw in ranked) / len(ranked)
            else:
                avg_position = None

            enriched.append(CompetitorDomain(
                domain=comp.domain,
                common_keywords=comp.common_keywords,
                avg_position=avg_position,
                organic_traffic=comp.organic_traffic,
                ranked_keywords=ranked,
            ))
        return enriched


def parse_keyword_response(data: dict) -> list[Keyword]:
    """Pure parser over the DataForSEO response shape. Defensive against gaps."""
    keywords: list[Keyword] = []
    for task in data.get("tasks") or []:
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                kw_info = item.get("keyword_info") or {}
                kw_props = item.get("keyword_properties") or {}
                intent_info = item.get("search_intent_info") or {}
                keywords.append(Keyword(
                    term=item.get("keyword", ""),
                    search_volume=_safe_int(kw_info.get("search_volume")),
                    difficulty=_safe_float(kw_props.get("keyword_difficulty")),
                    intent=(intent_info.get("main_intent") or "informational").lower(),
                ))
    return keywords


def parse_competitors_response(data: dict) -> list[CompetitorDomain]:
    """Pure parser for competitors_domain/live response. Defensive against gaps.

    The API returns items with domain, intersections (shared keywords with the
    target), and estimated_traffic. avg_position is NOT taken from this response
    (pos_1 is a rank-bucket count, not a mean position); it is computed later
    in fetch_competitors from the actual ranked-keywords positions.
    """
    competitors: list[CompetitorDomain] = []
    for task in data.get("tasks") or []:
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                raw_domain = item.get("domain") or item.get("url", "")
                if not raw_domain:
                    continue
                # Strip scheme/path so the stored value is always a bare host
                # (prevents corrupt ranked_keywords calls and bad hrefs in the UI).
                domain = _bare_host(raw_domain)
                competitors.append(CompetitorDomain(
                    domain=domain,
                    common_keywords=_safe_int(item.get("intersections")),
                    avg_position=None,  # computed by fetch_competitors after enrichment
                    organic_traffic=_safe_int(item.get("estimated_traffic")),
                    ranked_keywords=(),  # populated by fetch_competitors after this call
                ))
    return competitors


def parse_ranked_keywords_response(data: dict) -> tuple[RankedKeyword, ...]:
    """Pure parser for ranked_keywords/live response. Defensive against gaps.

    Each item has keyword_data (term + search_volume) and ranked_serp_element
    (position).
    """
    keywords: list[RankedKeyword] = []
    for task in data.get("tasks") or []:
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                kw_data = item.get("keyword_data") or {}
                kw_info = kw_data.get("keyword_info") or {}
                serp_el = item.get("ranked_serp_element") or {}
                serp_item = serp_el.get("serp_item") or {}
                keywords.append(RankedKeyword(
                    term=kw_data.get("keyword", ""),
                    position=_safe_float(serp_item.get("rank_absolute") or serp_item.get("position")),
                    search_volume=_safe_int(kw_info.get("search_volume")),
                ))
    return tuple(keywords)
