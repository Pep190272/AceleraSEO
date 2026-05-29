from aceleraseo.domain.autonomy import AutonomyMode, Decision, decide_action
from aceleraseo.domain.models import Action


def _action(risk="low"):
    return Action(kind="indexnow_ping", target_url="https://x.com/p",
                  description="ping", risk=risk, rationale="new page")


def test_none_mode_always_proposes():
    d = decide_action(_action("low"), AutonomyMode.NONE, 0, 999)
    assert d is Decision.PROPOSE


def test_limited_mode_auto_runs_low_risk_within_cap():
    d = decide_action(_action("low"), AutonomyMode.LIMITED, 0, 10)
    assert d is Decision.AUTO_EXECUTE


def test_limited_mode_proposes_high_risk_even_within_cap():
    d = decide_action(_action("high"), AutonomyMode.LIMITED, 0, 10)
    assert d is Decision.PROPOSE


def test_over_daily_cap_falls_back_to_proposal():
    d = decide_action(_action("low"), AutonomyMode.FULL, 10, 10)
    assert d is Decision.PROPOSE


def test_full_mode_auto_runs_any_risk_within_cap():
    d = decide_action(_action("high"), AutonomyMode.FULL, 0, 10)
    assert d is Decision.AUTO_EXECUTE
