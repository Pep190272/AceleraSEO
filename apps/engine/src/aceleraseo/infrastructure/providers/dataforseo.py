"""DataForSEO market-data adapter — implements domain.ports.MarketProvider.

Bring-your-own-key (ADR-0001): we orchestrate a third-party API, we do not own a
keyword index. The response parser is separated as a pure function so it is unit-
testable without network or credentials.
"""
from __future__ import annotations

import httpx

from ...domain.models import Keyword

_ENDPOINT = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live"


class DataForSEOMarketProvider:
    def __init__(self, login: str, password: str, timeout: float = 30.0):
        self._auth = (login, password)
        self._timeout = timeout

    def keyword_metrics(self, terms: list[str], location: str) -> list[Keyword]:
        payload = [{"keywords": terms, "location_name": location, "language_code": "es"}]
        resp = httpx.post(_ENDPOINT, auth=self._auth, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        return parse_keyword_response(resp.json())


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
                    search_volume=int(kw_info.get("search_volume") or 0),
                    difficulty=float(kw_props.get("keyword_difficulty") or 0.0),
                    intent=(intent_info.get("main_intent") or "informational").lower(),
                ))
    return keywords
