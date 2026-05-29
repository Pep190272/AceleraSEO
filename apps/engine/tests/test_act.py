from aceleraseo.application.act import ExecutePlan
from aceleraseo.domain.autonomy import AutonomyMode
from aceleraseo.domain.models import Action
from aceleraseo.infrastructure.persistence.db import make_session_factory
from aceleraseo.infrastructure.persistence.proposals import ProposalRepository


def _repo():
    return ProposalRepository(make_session_factory("sqlite:///:memory:"))


def _actions():
    return [
        Action("indexnow_ping", "https://x.com/new", "ping", "low", "new page"),
        Action("onpage_fix", "https://x.com/c", "fix noindex", "high", "crawl:noindex"),
    ]


def test_none_mode_queues_everything():
    repo = _repo()
    ran = []
    plan = ExecutePlan(repo, {"indexnow_ping": lambda a: ran.append(a)})
    res = plan.execute(_actions(), AutonomyMode.NONE, daily_cap=999)
    assert ran == []                       # nothing auto-executed
    assert len(res.proposed) == 2
    assert len(repo.pending()) == 2


def test_limited_mode_runs_low_risk_queues_high_risk():
    repo = _repo()
    ran = []
    plan = ExecutePlan(repo, {"indexnow_ping": lambda a: ran.append(a)})
    res = plan.execute(_actions(), AutonomyMode.LIMITED, daily_cap=10)
    assert len(res.executed) == 1          # the low-risk indexnow ping
    assert len(res.proposed) == 1          # the high-risk fix queued
    assert ran[0].kind == "indexnow_ping"


def test_action_without_executor_is_proposed_even_if_auto():
    repo = _repo()
    plan = ExecutePlan(repo, executors={})  # no executors registered
    res = plan.execute(_actions(), AutonomyMode.FULL, daily_cap=10)
    assert res.executed == []
    assert len(res.proposed) == 2


def test_proposal_status_transitions():
    repo = _repo()
    pid = repo.enqueue(_actions()[0])
    assert repo.set_status(pid, "approved") is True
    assert repo.pending() == []            # no longer pending
    assert repo.set_status(99999, "approved") is False
