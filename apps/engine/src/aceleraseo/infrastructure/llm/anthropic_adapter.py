"""Anthropic LLM adapter — implements domain.ports.LLMPort.

Writes the strategic executive summary. Uses prompt caching on the (stable)
system prompt so repeated strategy runs are cheaper and faster — the system
prompt is identical across calls, only the user payload changes.
"""
from __future__ import annotations

from ...domain.models import Action, BusinessProfile, ScoredKeyword

_SYSTEM_PROMPT = (
    "You are a senior SEO strategist. Given a business profile, a ranked list of "
    "winnable keywords, and a list of prioritised actions, write a concise, honest "
    "executive summary (max ~150 words). Explain the strategic logic: why these "
    "keywords are winnable for this authority level, what to fix first and why, and "
    "the expected sequence of impact. Never promise guaranteed rankings. Be direct."
)


class AnthropicLLM:
    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def explain_strategy(
        self,
        profile: BusinessProfile,
        keywords: list[ScoredKeyword],
        actions: list[Action],
    ) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            system=[{
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},   # cache the stable prefix
            }],
            messages=[{"role": "user", "content": _render(profile, keywords, actions)}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


def _render(profile: BusinessProfile, keywords: list[ScoredKeyword],
            actions: list[Action]) -> str:
    kw_lines = "\n".join(
        f"- {s.keyword.term} (vol={s.keyword.search_volume}, "
        f"diff={s.keyword.difficulty}, opportunity={s.opportunity})"
        for s in keywords
    )
    action_lines = "\n".join(
        f"- [{a.risk}] {a.kind}: {a.description}" for a in actions
    )
    return (
        f"BUSINESS PROFILE\n"
        f"type={profile.type.value}, maturity={profile.maturity.value}, "
        f"authority={profile.authority_band.value}, "
        f"geo_relevant={profile.is_geo_relevant}\n\n"
        f"WINNABLE KEYWORDS (ranked)\n{kw_lines}\n\n"
        f"PRIORITISED ACTIONS\n{action_lines}\n"
    )
