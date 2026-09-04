# ADR 0003 — Pause (Jul–Aug 2026), and the decision to resume

- Status: Accepted
- Date: 2026-09-04
- Records two things: why work stopped, and why it restarts.

## Part A — The pause that happened

Active development stopped after 2026-07-02. Between then and 2026-08-24 the repo
received only CI fixes — no features. No commit, ADR, issue or TODO recorded why, so when
the project was picked up on 2026-09-04 the reason had to be reconstructed from scratch.

The working assumption on resuming was that the project had stalled because **reaching
the goal required paying for subscriptions**. That was checked against the code and it is
**false**. It is written down here so nobody re-derives it a third time.

### The cost belief is wrong — evidence

Only two external providers charge money: **DataForSEO** and **Anthropic**. Everything the
core loop needs is free: Search Console, GA4, URL Inspection, IndexNow, and the
self-hosted crawler. Full breakdown in `docs/API-LIMITS.md`.

With zero spend:

- `POST /strategy/preview` still returns a complete plan. `make_llm()` falls back to
  `NullLLM` when no real key is set
  (`apps/engine/src/aceleraseo/infrastructure/llm/factory.py:26`). This is deliberate —
  `null_llm.py:3-4` states: *"The brain must work without a paid LLM. This produces a
  plain templated summary so DECIDE always returns a usable plan; the real LLM only
  upgrades the prose."*
- `POST /sense/run`, `POST /audit/run`, all four `/act/*` endpoints and
  `GET /learn/outcome` need no paid provider.
- **18 of the 20 engine endpoints work without paying anything.**

Exactly two degrade, and both fail with a clear message rather than an error:

| Endpoint | Without payment | Where |
|---|---|---|
| `POST /strategy/discover` | `422` — needs an LLM key | `interfaces/api/app.py:174-179` |
| `POST /competitors/analyze` | `503` — needs DataForSEO credentials | `interfaces/api/app.py:398-402` |

There is a real hidden cost, and it is not a subscription: without DataForSEO you supply
`search_volume` and `difficulty` by hand per keyword — caller-provided fields defaulting
to zero (`interfaces/api/app.py:139-143`). The price is manual work, not a monthly bill.

### What actually stalled it

**Priority.** The last feature was authored 2026-07-02, the same day the repo started
ignoring local job-hunt documents; it then sat uncommitted for seven weeks. Attention
moved elsewhere. Nothing technical blocked the work.

A secondary factor: `.env` was never filled in, so the loop had never run against real
Search Console or Analytics data — which makes a project easy to put down.

## Part B — The decision (2026-09-04): resume

The project is **not** parked. Work continues, in spare slots, following `docs/PLAN.md`.

What changed is the framing. AceleraSEO is a **showcase for the AceleraI brand**: open
source not as a distribution model but as a calling card for the work. That reading sits
alongside the two already in the repo — a self-hostable tool for the community, and a
practical instrument for the author's own SEO analysis. All three are compatible;
`docs/PLAN.md` explains how they coexist and where they conflict.

### Why the framing is the important part

It changes what counts as a defect. The test for every finding stops being *"does it
work?"* and becomes **"what impression does this leave on someone who does not know us?"**
Under that test, three things previously filed as cosmetic become product defects:

- A stranger arriving from GitHub cannot start the project — the README's Quick start
  points at `docs/ARCHITECTURE.md`, which names Docker Compose in a tooling table
  (`ARCHITECTURE.md:99`) but carries no runnable instruction. That is not a documentation
  gap; it is the lost first impression, which is the whole reason the repo is public.
- `SESSION-HANDOFF.md` declares M0–M6 all done while `ROADMAP.md:5` marks only M0. In a
  private repo that is untidy. In a public one it reads as either careless or overstated.
- SENSE, ACT and LEARN exist only behind `curl`. A visitor cannot see the loop the README
  promises actually run.

## Consequences

- (+) The cost misconception is recorded with evidence and will not cost another session.
- (+) Defects are now prioritised by the impression they leave, not by how hard they are.
- (−) Under the showcase test the repo is further from "presentable" than the milestone
  table suggests. `docs/PLAN.md` states the cut line for a presentable v1.

## Sequencing

Josep was explicit: **the plan first, then fixes.** `docs/PLAN.md` is written before any
production code changes. Implementation begins from its slices, in order, starting with
Google OAuth plus a "run SENSE" control in the UI — the change that turns three quarters
of this system from a library into something a visitor can watch work.
