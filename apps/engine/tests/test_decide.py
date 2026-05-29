from aceleraseo.application.decide import BuildStrategy
from aceleraseo.domain.models import (
    AuditIssue,
    Keyword,
    Severity,
    SiteSnapshot,
)
from aceleraseo.infrastructure.llm.null_llm import NullLLM


class SpyLLM:
    def __init__(self):
        self.called_with = None

    def explain_strategy(self, profile, keywords, actions):
        self.called_with = (profile, keywords, actions)
        return "SUMMARY"


def _kws():
    return [
        Keyword(term="head term", search_volume=40000, difficulty=85, intent="commercial"),
        Keyword(term="winnable long tail", search_volume=300, difficulty=12,
                intent="transactional"),
    ]


def test_plan_ranks_winnable_first_for_low_authority():
    snap = SiteSnapshot(ranking_query_count=10, has_local_signals=True)
    plan = BuildStrategy(NullLLM()).execute(snap, _kws())
    assert plan.keywords[0].keyword.term == "winnable long tail"
    assert plan.executive_summary  # NullLLM still fills it


def test_critical_crawl_issue_becomes_high_risk_action():
    snap = SiteSnapshot(ranking_query_count=10)
    issues = [AuditIssue(code="noindex", severity=Severity.CRITICAL,
                         url="https://x.com/c", message="noindex")]
    plan = BuildStrategy(NullLLM()).execute(snap, _kws(), crawl_issues=issues)
    fix = next(a for a in plan.actions if a.kind == "onpage_fix")
    assert fix.risk == "high"
    assert fix.target_url == "https://x.com/c"


def test_notice_issues_do_not_create_actions():
    snap = SiteSnapshot(ranking_query_count=10)
    issues = [AuditIssue(code="thin_content", severity=Severity.NOTICE,
                         url="https://x.com/p", message="thin")]
    plan = BuildStrategy(NullLLM()).execute(snap, _kws(), crawl_issues=issues)
    assert all(a.kind != "onpage_fix" for a in plan.actions)


def test_llm_receives_profile_and_scored_keywords():
    spy = SpyLLM()
    snap = SiteSnapshot(ranking_query_count=10)
    plan = BuildStrategy(spy).execute(snap, _kws())
    assert plan.executive_summary == "SUMMARY"
    profile, keywords, _ = spy.called_with
    assert profile is plan.profile
    assert keywords == plan.keywords
