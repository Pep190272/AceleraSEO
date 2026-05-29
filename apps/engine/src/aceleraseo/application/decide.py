"""DECIDE use case — turn signals into an explained, prioritised ActionPlan.

Flow (deterministic core, LLM as enhancement):
  1. classify the business from the snapshot
  2. score every candidate keyword for THIS profile (winnable, not just big)
  3. derive concrete actions from crawl issues + the top keywords
  4. ask the LLM to write an executive summary (optional — degrades gracefully)

Depends only on domain rules + the LLMPort, so it is fully testable with a fake
LLM and no network.
"""
from __future__ import annotations

from ..domain.classify import classify
from ..domain.models import (
    Action,
    ActionPlan,
    AuditIssue,
    Keyword,
    Severity,
    SiteSnapshot,
)
from ..domain.ports import LLMPort
from ..domain.strategy import score_keyword

_RISK_BY_SEVERITY = {
    Severity.CRITICAL: "high",
    Severity.WARNING: "medium",
    Severity.NOTICE: "low",
}


class BuildStrategy:
    def __init__(self, llm: LLMPort):
        self._llm = llm

    def execute(
        self,
        snapshot: SiteSnapshot,
        candidate_keywords: list[Keyword],
        crawl_issues: list[AuditIssue] | None = None,
        top_n: int = 10,
    ) -> ActionPlan:
        profile = classify(snapshot)

        scored = sorted(
            (score_keyword(kw, profile) for kw in candidate_keywords),
            key=lambda s: s.opportunity,
            reverse=True,
        )[:top_n]

        actions = self._derive_actions(scored, crawl_issues or [])

        # The LLM only narrates — it must never break the plan. If it fails at
        # runtime (bad/expired key, rate limit, outage), degrade to the
        # deterministic NullLLM summary instead of 500ing.
        try:
            summary = self._llm.explain_strategy(profile, scored, actions)
        except Exception:
            from ..infrastructure.llm.null_llm import NullLLM
            summary = NullLLM().explain_strategy(profile, scored, actions)

        return ActionPlan(
            profile=profile,
            keywords=scored,
            actions=actions,
            executive_summary=summary,
        )

    def _derive_actions(self, scored, issues: list[AuditIssue]) -> list[Action]:
        actions: list[Action] = []

        # Fix what is technically broken first — ranking is impossible otherwise.
        for issue in issues:
            if issue.severity is Severity.NOTICE:
                continue
            actions.append(Action(
                kind="onpage_fix",
                target_url=issue.url,
                description=issue.message,
                risk=_RISK_BY_SEVERITY[issue.severity],
                rationale=f"crawl:{issue.code}",
            ))

        # Then pursue the most winnable keywords with new/updated content.
        for s in scored[:3]:
            actions.append(Action(
                kind="content_brief",
                target_url="",
                description=f"Create/optimise content targeting '{s.keyword.term}'.",
                risk="low",
                rationale=s.rationale,
            ))

        return actions
