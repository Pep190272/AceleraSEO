"""LEARN — pure outcome measurement. No I/O, fully testable.

This closes the loop. Given two windows of ranking signals (before an action and
after), it computes per-query movement so DECIDE can adjust next cycle. The whole
agent is Sense -> Decide -> Act -> *Learn* -> back to Decide; this module is the
arrow that points back.

Position semantics: LOWER is better (position 1 = top). A negative position_change
means the query moved UP the SERP = improvement.
"""
from __future__ import annotations

from collections import defaultdict

from .models import OutcomeDelta, OutcomeReport, RankingSignal, Trend

# A move smaller than this (in average SERP position) is noise, not signal.
_STABLE_BAND = 0.5


def _aggregate(signals: list[RankingSignal]) -> dict[str, tuple[float, int]]:
    """Average position (impression-weighted) and total clicks per query."""
    pos_num: dict[str, float] = defaultdict(float)
    pos_den: dict[str, int] = defaultdict(int)
    clicks: dict[str, int] = defaultdict(int)
    for s in signals:
        weight = max(s.impressions, 1)
        pos_num[s.query] += s.position * weight
        pos_den[s.query] += weight
        clicks[s.query] += s.clicks
    return {q: (pos_num[q] / pos_den[q], clicks[q]) for q in pos_num}


def _classify(before: float | None, after: float | None) -> Trend:
    if before is None and after is not None:
        return Trend.NEW
    if before is not None and after is None:
        return Trend.LOST
    if before is None or after is None:
        return Trend.STABLE
    change = after - before
    if change <= -_STABLE_BAND:
        return Trend.IMPROVED      # position decreased -> moved up
    if change >= _STABLE_BAND:
        return Trend.DECLINED
    return Trend.STABLE


def evaluate_outcome(
    before: list[RankingSignal],
    after: list[RankingSignal],
) -> OutcomeReport:
    agg_before = _aggregate(before)
    agg_after = _aggregate(after)

    report = OutcomeReport()
    for query in sorted(set(agg_before) | set(agg_after)):
        pos_b, clk_b = agg_before.get(query, (None, 0))
        pos_a, clk_a = agg_after.get(query, (None, 0))
        report.deltas.append(OutcomeDelta(
            query=query,
            position_before=round(pos_b, 2) if pos_b is not None else None,
            position_after=round(pos_a, 2) if pos_a is not None else None,
            clicks_before=clk_b,
            clicks_after=clk_a,
            trend=_classify(pos_b, pos_a),
        ))
    return report
