"""Autonomy gate — pure decision logic for whether an action may auto-execute.

ADR-0002: an agent rewriting a live production site unsupervised is a liability.
This function is the single chokepoint. It is pure (no I/O) so the safety rules
are fully testable and auditable.

Modes:
  none    — nothing auto-executes; everything becomes a proposal for human review.
  limited — only LOW-risk actions auto-execute, within the daily cap.
  full    — any action auto-executes, within the daily cap (not recommended live).
"""
from __future__ import annotations

from enum import Enum

from .models import Action


class AutonomyMode(str, Enum):
    NONE = "none"
    LIMITED = "limited"
    FULL = "full"


class Decision(str, Enum):
    AUTO_EXECUTE = "auto_execute"
    PROPOSE = "propose"           # queue for human approval


def decide_action(
    action: Action,
    mode: AutonomyMode,
    actions_used_today: int,
    daily_cap: int,
) -> Decision:
    if mode is AutonomyMode.NONE:
        return Decision.PROPOSE

    if actions_used_today >= daily_cap:
        return Decision.PROPOSE       # over budget → fall back to proposal

    if mode is AutonomyMode.LIMITED and action.risk != "low":
        return Decision.PROPOSE       # limited mode never auto-runs risky changes

    return Decision.AUTO_EXECUTE
