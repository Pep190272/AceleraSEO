"""Deterministic LLM stand-in — used when no API key is configured.

The brain must work without a paid LLM. This produces a plain templated summary
so DECIDE always returns a usable plan; the real LLM only upgrades the prose.
"""
from __future__ import annotations

from ...domain.models import Action, BusinessProfile, ScoredKeyword


class NullLLM:
    def explain_strategy(
        self,
        profile: BusinessProfile,
        keywords: list[ScoredKeyword],
        actions: list[Action],
    ) -> str:
        top = ", ".join(s.keyword.term for s in keywords[:3]) or "(no candidates)"
        fixes = sum(1 for a in actions if a.kind == "onpage_fix")
        return (
            f"Profile: {profile.type.value}, {profile.maturity.value}, "
            f"authority={profile.authority_band.value}. "
            f"Priority keywords: {top}. "
            f"{fixes} technical fix(es) queued before content work. "
            f"(Set an LLM API key for a full strategic narrative.)"
        )
