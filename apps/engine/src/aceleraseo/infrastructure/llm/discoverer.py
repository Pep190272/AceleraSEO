"""LLM keyword discoverer — implements domain.ports.KeywordDiscoverer.

Given a plain-language business description, asks Claude for candidate keywords
a real customer would search, each with a rough volume/difficulty/intent. These
estimates can later be replaced by real DataForSEO metrics. The JSON parser is a
pure function so it is testable without the network.
"""
from __future__ import annotations

import json

from ...domain.models import Keyword

_SYSTEM_PROMPT = (
    "You are an expert SEO keyword researcher. Given a business description, a "
    "location and a language, return ONLY a JSON array (no prose, no markdown) of "
    "candidate keywords a real customer would type into Google. Mix a few "
    "high-volume head terms with many winnable long-tail and local variations. "
    'Each item must be: {"term": string in the requested language, '
    '"search_volume": integer rough monthly estimate, '
    '"difficulty": integer 0-100, '
    '"intent": one of "informational"|"commercial"|"transactional"|"navigational"}. '
    "Return 12 to 20 items."
)

_VALID_INTENTS = {"informational", "commercial", "transactional", "navigational"}


class AnthropicKeywordDiscoverer:
    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def discover(
        self, description: str, location: str, language: str, max_keywords: int = 20
    ) -> list[Keyword]:
        user = (
            f"Business: {description}\n"
            f"Location: {location or 'not specified'}\n"
            f"Language for keywords: {language}\n"
            f"Return at most {max_keywords} keywords."
        )
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        return parse_keywords_json(text, max_keywords)


def parse_keywords_json(text: str, max_keywords: int = 20) -> list[Keyword]:
    """Pure parser: tolerate markdown fences and stray prose around the JSON."""
    cleaned = _extract_json_array(text)
    try:
        items = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(items, list):
        return []

    keywords: list[Keyword] = []
    for item in items[:max_keywords]:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        if not term:
            continue
        intent = str(item.get("intent", "informational")).lower()
        if intent not in _VALID_INTENTS:
            intent = "informational"
        keywords.append(Keyword(
            term=term,
            search_volume=_safe_int(item.get("search_volume")),
            difficulty=_safe_float(item.get("difficulty")),
            intent=intent,
        ))
    return keywords


def _extract_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return "[]"
    return text[start : end + 1]


def _safe_int(value) -> int:
    try:
        return max(int(float(value)), 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value) -> float:
    try:
        return min(max(float(value), 0.0), 100.0)
    except (TypeError, ValueError):
        return 0.0
