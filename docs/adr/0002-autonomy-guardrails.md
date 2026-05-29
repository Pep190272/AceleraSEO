# ADR 0002 — Autonomy defaults to propose-only

- Status: Accepted
- Date: 2026-05-29

## Context
The goal is an autonomous SEO that controls "all aspects" of a business's SEO,
including acting when new content is published. An agent writing to a live
production site unsupervised is a serious liability (wrong edits, ranking loss,
brand damage, irreversible changes).

## Decision
`AUTONOMY_MODE` defaults to `none` (propose-only, human approves each action).
`limited` and `full` are opt-in with hard daily caps (`MAX_AUTO_ACTIONS_PER_DAY`).
Every action is logged with before/after state and the reasoning that produced it.

## Consequences
- (+) Safe by default; builds user trust.
- (+) Fully auditable and reversible.
- (−) Out of the box it is assistive, not hands-off — by design.
