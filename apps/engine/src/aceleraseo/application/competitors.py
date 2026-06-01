"""COMPETITORS use case — find the top organic competitors for a domain.

Flow: asks the CompetitorProvider (DataForSEO) for domains that compete with the
target, then fetches the ranked keywords for each competitor. If the provider is
absent or a per-competitor keywords call fails, the use case degrades gracefully
rather than failing the whole request — mirrors how DiscoverKeywords handles a
missing or broken MarketProvider.
"""
from __future__ import annotations

from ..domain.models import CompetitorDomain
from ..domain.ports import CompetitorProvider

# Named constants keep the N+1 cost-control limits visible and configurable.
MAX_COMPETITORS = 5
MAX_KEYWORDS_PER_COMPETITOR = 10


class AnalyzeCompetitors:
    def __init__(self, provider: CompetitorProvider):
        self._provider = provider

    def execute(
        self,
        target: str,
        location: str = "",
        language: str = "es",
        max_competitors: int = MAX_COMPETITORS,
        max_keywords_per_competitor: int = MAX_KEYWORDS_PER_COMPETITOR,
    ) -> list[CompetitorDomain]:
        # Clamp caller-supplied limits to the module maxima so the application
        # layer is the authority on cost-control ceilings regardless of what
        # the API caller passes.
        clamped_competitors = min(max_competitors, MAX_COMPETITORS)
        clamped_keywords = min(max_keywords_per_competitor, MAX_KEYWORDS_PER_COMPETITOR)
        return self._provider.fetch_competitors(
            target=target,
            location=location,
            language=language,
            max_competitors=clamped_competitors,
            max_keywords_per_competitor=clamped_keywords,
        )
