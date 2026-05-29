# ADR 0001 — No self-hosted backlink index

- Status: Accepted
- Date: 2026-05-29

## Context
The initial intuition was to build an open-source clone of Ahrefs whose differentiator
is "the code being open." Research shows Ahrefs' moat is its data: 456B pages, 35T
backlinks, ~$300M/yr infrastructure. Code openness does not overcome a data moat.

## Decision
We will NOT build a web-scale crawler or backlink index. Backlink data is obtained via
third-party APIs using the user's own key (bring-your-own-key). Our differentiation is
the **decision/strategy layer + closed feedback loop over the user's own GSC/GA4**, not
data volume.

## Consequences
- (+) Tractable, self-hostable, honest scope.
- (+) Differentiation Ahrefs structurally lacks (they don't touch your GSC/GA4).
- (−) Backlink depth depends on the chosen provider; not a core strength.
- (−) Users need at least one market-data API key.
