"""ACT use case — execute or propose each action per the autonomy gate.

For every action the deterministic gate (domain/autonomy.py) decides: auto-run
now, or queue as a proposal for a human. Auto-runnable executors are injected;
unknown kinds always fall back to a proposal (safe default).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.autonomy import AutonomyMode, Decision, decide_action
from ..domain.models import Action


@dataclass
class ActResult:
    executed: list[str] = field(default_factory=list)
    proposed: list[int] = field(default_factory=list)


class ExecutePlan:
    def __init__(self, proposals, executors: dict | None = None):
        """executors: kind -> callable(Action) -> None for auto-runnable actions."""
        self._proposals = proposals
        self._executors = executors or {}

    def execute(
        self,
        actions: list[Action],
        mode: AutonomyMode,
        actions_used_today: int = 0,
        daily_cap: int = 0,
    ) -> ActResult:
        result = ActResult()
        used = actions_used_today

        for action in actions:
            decision = decide_action(action, mode, used, daily_cap)
            executor = self._executors.get(action.kind)

            if decision is Decision.AUTO_EXECUTE and executor is not None:
                executor(action)
                result.executed.append(action.kind)
                used += 1
            else:
                # PROPOSE, or no executor available for this kind → queue it.
                result.proposed.append(self._proposals.enqueue(action))

        return result
