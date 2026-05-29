"""DISCOVER use case — turn a business description into candidate keywords.

Flow: the LLM proposes keywords for the niche; if a MarketProvider (DataForSEO)
is configured, its real volume/difficulty replace the LLM's estimates. Falls
back to the estimates if the market call fails — discovery still works.
"""
from __future__ import annotations

from ..domain.models import Keyword
from ..domain.ports import KeywordDiscoverer, MarketProvider


class DiscoverKeywords:
    def __init__(self, discoverer: KeywordDiscoverer, market: MarketProvider | None = None):
        self._discoverer = discoverer
        self._market = market

    def execute(
        self,
        description: str,
        location: str = "",
        language: str = "en",
        max_keywords: int = 20,
    ) -> list[Keyword]:
        candidates = self._discoverer.discover(description, location, language, max_keywords)
        if not candidates or self._market is None:
            return candidates
        return self._enrich(candidates, location)

    def _enrich(self, candidates: list[Keyword], location: str) -> list[Keyword]:
        try:
            real = self._market.keyword_metrics([k.term for k in candidates], location)
        except Exception:
            return candidates  # market lookup failed → keep LLM estimates
        by_term = {r.term.lower(): r for r in real}
        merged: list[Keyword] = []
        for kw in candidates:
            hit = by_term.get(kw.term.lower())
            # Keep the LLM intent (DataForSEO intent can be sparse); take real numbers.
            merged.append(
                Keyword(term=kw.term, search_volume=hit.search_volume,
                        difficulty=hit.difficulty, intent=kw.intent)
                if hit else kw
            )
        return merged
