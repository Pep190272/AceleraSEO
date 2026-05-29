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

# Max keyword difficulty a site can realistically rank for, per authority band.
# Above this ceiling, opportunity collapses steeply — chasing it wastes months.
_DIFFICULTY_CEILING = {
    AuthorityBand.LOW: 30.0,
    AuthorityBand.MID: 55.0,
    AuthorityBand.HIGH: 100.0,
}

# How hard unwinnable terms are punished once over the ceiling.
_INFEASIBILITY_EXPONENT = 4.0


def _feasibility(difficulty: float, band: AuthorityBand) -> float:
    """1.0 when the term is within reach; decays fast past the authority ceiling.

    This is the honest core: raw search volume is worthless if the site cannot
    realistically rank. A low-authority site facing difficulty 85 gets a near-zero
    factor, so winnable long-tail beats impossible heads — exactly the right call.
    """
    ceiling = _DIFFICULTY_CEILING[band]
    if difficulty <= ceiling:
        return 1.0
    return (ceiling / difficulty) ** _INFEASIBILITY_EXPONENT


def score_keyword(kw: Keyword, profile: BusinessProfile) -> ScoredKeyword:
    """opportunity = intent x volume x value x feasibility / difficulty

    Feasibility gates volume by what the site can actually win, steering new /
    low-authority sites toward winnable long-tail and letting established sites
    chase competitive heads.
    """
    intent_w = _INTENT_WEIGHT.get(kw.intent, 1.0)
    difficulty = max(kw.difficulty, 1.0)
    feasibility = _feasibility(kw.difficulty, profile.authority_band)

    numerator = intent_w * kw.search_volume * kw.business_value * feasibility
    opportunity = numerator / difficulty

    # New geo-relevant businesses: boost local-friendly low-difficulty long-tail.
    if profile.maturity is Maturity.NEW and profile.is_geo_relevant and kw.difficulty < 30:
        opportunity *= 1.5

    rationale = (
        f"intent={kw.intent}(x{intent_w}), vol={kw.search_volume}, "
        f"diff={kw.difficulty}, feasibility={feasibility:.2f} -> {opportunity:.1f}"
    )
    return ScoredKeyword(keyword=kw, opportunity=round(opportunity, 2), rationale=rationale)
