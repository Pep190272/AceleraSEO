"""The strategy brain — pure scoring rules. The LLM refines/explains on top of this."""
from __future__ import annotations

from .models import (
    AuthorityBand,
    BusinessProfile,
    Keyword,
    Maturity,
    ScoredKeyword,
)

_INTENT_WEIGHT = {
    "transactional": 1.4,
    "commercial": 1.2,
    "informational": 1.0,
    "navigational": 0.6,
}

_AUTHORITY_GAP = {
    AuthorityBand.LOW: 3.0,
    AuthorityBand.MID: 1.6,
    AuthorityBand.HIGH: 1.0,
}


def score_keyword(kw: Keyword, profile: BusinessProfile) -> ScoredKeyword:
    """opportunity = (intent x volume x value) / (difficulty x authority_gap)

    A low-authority/new site is penalised on high-difficulty terms, steering it
    toward winnable long-tail. An established site can chase competitive heads.
    """
    intent_w = _INTENT_WEIGHT.get(kw.intent, 1.0)
    gap = _AUTHORITY_GAP[profile.authority_band]
    difficulty = max(kw.difficulty, 1.0)

    numerator = intent_w * kw.search_volume * kw.business_value
    opportunity = numerator / (difficulty * gap)

    # New local businesses: boost geo-friendly long-tail (low difficulty).
    if profile.maturity is Maturity.NEW and profile.is_geo_relevant and kw.difficulty < 30:
        opportunity *= 1.5

    rationale = (
        f"intent={kw.intent}(x{intent_w}), vol={kw.search_volume}, "
        f"diff={kw.difficulty}, authority_gap=x{gap} -> {opportunity:.1f}"
    )
    return ScoredKeyword(keyword=kw, opportunity=round(opportunity, 2), rationale=rationale)
