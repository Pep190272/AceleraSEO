# AceleraSEO — plan

Written 2026-09-04, before any fixes, on purpose. Background: [ADR-0003](./adr/0003-pause-and-resume.md).

The project resumes. This document is the architecture and delivery plan it resumes from.

---

## 1. What this is, and who it is for

Three readings of the goal exist in this repo. All three are real, they arrived in this
order, and they mostly agree.

**1. Open source for self-hosters** — the founding intent. Initial commit `d5caf0a`
(2026-05-29): *"autonomous SEO strategy engine"*. MIT, bring-your-own-API-key, your data
stays yours (`README.md`). `ROADMAP.md` M6 plans a docs site and a contribution guide.

**2. A showcase for the AceleraI brand** — the reason the repo is public. Open source here
is a calling card: it exists so somebody can look at the work and judge the craft. This
reading was not written down before this document, and it is the one that decides
priorities.

**3. A tool for the author's own sites** — where it actually drifted. The last feature
built (2026-07-02) was the Noor CMS adapter: an integration with one specific site
(`NOOR_BASE_URL` / `NOOR_API_KEY`, `infrastructure/config.py`).

**How they coexist.** Readings 1 and 2 pull the same way: both are served by a repo a
stranger can clone, start, and see working. Reading 3 pulls differently — a private
integration with one client site is useful to Josep and meaningless to a visitor.

The resolution: **treat 3 as a proof, not as the product.** The Noor adapter demonstrates
that the `CMSPort` abstraction works against a real system. Keep it, present it as one
adapter among possible others, and never let it become the only path that works. Where
readings conflict, 2 wins — the repo is public first.

### The test

For every finding, the question is not *"does it work?"* but:

> **What impression does this leave on someone who does not know us?**

That single change reclassifies most of the open defects below from cosmetic to blocking.

---

## 2. Definition of done

For a public repo whose job is to make an impression:

> **A stranger who has never seen this project goes from landing on the GitHub page to a
> working instance in their browser in under 10 minutes, without asking anyone anything.**

Ten minutes, on a machine with Docker installed. What that requires:

| Requirement | Today |
|---|---|
| README says exactly how to start it | ❌ Quick start points at `ARCHITECTURE.md`, which has no runnable instruction — only a tooling table row at `ARCHITECTURE.md:99` |
| It starts with one command | ✅ `docker compose up` works |
| It does something visible with no keys at all | ⚠️ Partly — Strategy and Audit work keyless; the rest looks broken |
| The status claim matches reality | ❌ `SESSION-HANDOFF.md` says M0–M6 done, `ROADMAP.md:5` marks only M0 |
| Advertised features are reachable | ❌ SENSE, ACT and LEARN are `curl`-only |
| Nothing advertised is missing | ❌ Core Web Vitals and index-status alerts are claimed and not implemented |

Five of six fail. That gap, not the feature count, is the actual state of the project.

---

## 3. Architecture

### What holds

The hexagonal shape is sound and should not be revisited. Domain logic is pure and
testable; Google, LLM, market data and crawling sit behind ports as swappable adapters.
The two founding ADRs still hold: no self-hosted backlink index
([ADR-0001](./adr/0001-no-self-hosted-backlink-index.md)) and propose-only autonomy by
default ([ADR-0002](./adr/0002-autonomy-guardrails.md)).

The engine is complete in a way the UI is not. All four loop stages are implemented,
tested and exposed over HTTP.

### What is missing

**A UI layer for three of the four loop stages.** This is the whole problem, and it is not
an architectural flaw — the ports are right, the adapters exist, the HTTP surface exists.
What is missing is the last hop:

| Stage | Engine | Dashboard |
|---|---|---|
| SENSE | ✅ `/sense/run`, `/auth/google/*` | ❌ nothing — no OAuth button exists |
| DECIDE | ✅ `/strategy/preview`, `/strategy/discover` | ✅ Strategy tab |
| ACT | ✅ `/act/indexnow`, `/act/index-status`, `/act/proposals` | ❌ nothing |
| LEARN | ✅ `/learn/outcome` | ❌ nothing |

Nine of twenty engine endpoints are reachable by clicking. The Settings tab collects
`gsc_site_url`, `ga4_property_id`, `google_oauth_client_id` and
`google_oauth_client_secret` — four fields that currently lead nowhere, because nothing in
the UI ever starts the consent flow or triggers a collection run.

**A read endpoint over the collected time series.** `/sense/run` persists data; nothing
serves it back for display. Slice 3 needs this.

### What is dead or hollow

- **`SiteTool.tsx`** — complete component, typed client, proxy routes, full bilingual
  copy, and **imported nowhere**. Absent from `apps/dashboard/src/lib/tab-config.ts:17-22`.
  It is the only path in the system that writes to a live site.
- **The `site.*` i18n block** — `apps/dashboard/src/lib/i18n.tsx:137` (ES) and `:316` (EN),
  plus the `nav.site` labels at `:37` and `:216`. Copy for a tab that does not exist.
- **`serpapi_key`** — declared at `infrastructure/config.py:52` with **no adapter written**.
  There is no `providers/serpapi.py`. The setting is a promise the code does not keep.
  Either write the adapter (it would be the second market-data adapter, which is what
  `ARCHITECTURE.md` claims the hexagonal shape buys) or remove the field.
- **Claimed and not implemented** — Core Web Vitals in the audit table (`README.md:38`);
  no LCP/CLS/INP anywhere in `domain/audit.py` or `providers/crawler.py`. Index-status
  *"monitoring + alerts"* (`README.md:42`); `/act/index-status` is a single synchronous
  one-URL check with no scheduler and no alert channel.

### Ports worth adding, in order of value

1. **`SearchConsolePort` read-back** — serve the persisted series (blocks slice 3).
2. **A second `MarketPort` adapter** — SerpApi, to prove the port abstraction is real
   rather than aspirational. Low urgency; high demonstrative value for a showcase repo.
3. **A second `CMSPort` adapter** — WordPress. Turns Noor from a private integration into
   an example of a pattern. Only worth it under readings 1 and 2.

---

## 4. Gap inventory, by impression

Ordered by what a stranger notices, not by difficulty.

| # | Gap | Impression it leaves | Where |
|---|---|---|---|
| 1 | Cannot start it from the README | "They didn't bother." First and worst. | `README.md:68-72`, `ARCHITECTURE.md:99` |
| 2 | Status contradicts itself | "Which do I believe?" Costs credibility on a public repo. | `ROADMAP.md:5` vs `SESSION-HANDOFF.md:33-49` |
| 3 | Hero copy says "Try it below" for four verbs; only one is below | Overstatement, discovered within a minute. | `i18n.tsx:225-226`, `:46` |
| 4 | SENSE / ACT / LEARN unreachable | The demo cannot show what the README promises. | §3 above |
| 5 | Features claimed, not implemented | Reads as padding. | `README.md:38`, `:42` |
| 6 | Dead component with full copy shipped | Sloppiness, visible to anyone reading the source — which is the point of a showcase. | `SiteTool.tsx`, `i18n.tsx:137,316` |
| 7 | Setting with no adapter | Same. | `config.py:52` |

Gaps 1, 2, 3 and 5 are **documentation and copy**, fixable in about three hours total, and
they are four of the top five. The expensive one is gap 4.

---

## 5. Slices

Each is closeable in **1–2 hours**, is worth something on its own, and can be verified
when finished. None requires a paid provider.

### Slice 0 — Make it runnable again (~30 min)

Prerequisite. Two mechanical problems:

1. **`.env` holds only variable names, never filled in.** At minimum: Google OAuth client
   id/secret and `GSC_SITE_URL`. Everything else can stay empty — `docs/API-LIMITS.md`
   says what each missing key costs.
2. **The running image is stale.** `aceleraseo/engine:latest` was built 2026-05-31; the
   code is from 2026-08-24. The running container has no `/cms/*` and no
   `/competitors/analyze`. `docker compose up -d --build`.

Safe: there are no migrations. `Base.metadata.create_all(engine)` runs on every start
(`infrastructure/persistence/db.py`) and the data volume survives a rebuild.

**Verify:** `GET /openapi.json` lists `/competitors/analyze` and `/cms/audit`.

### Slice 1 — Connect Google from the UI (~2 h) ← start here

The highest-value change in this document. It unblocks slices 2, 3 and 4 and turns three
quarters of the system from a library into something visible.

- **Touch:** `SettingsTool.tsx` (a "Connect Google" button), a proxy route under
  `src/app/api/auth/`, a connection-state indicator.
- **Engine:** already done — `/auth/google/login` and `/auth/google/callback` exist.
- **Verify:** click, complete consent, land back in Settings showing "connected".
- **Free.**

### Slice 2 — Run SENSE from the UI (~1 h)

With slice 1 done, a button and a result panel.

- **Touch:** a "Run collection" control POSTing to `/sense/run` via a new proxy route.
- **Verify:** press it, see row counts for rankings and conversions.
- **Free.**

### Slice 3 — Show what SENSE collected (~2 h)

`ROADMAP.md` M1 promises *"what's ranking, what's converting, what's slipping"*. Never
built, and it is the first screen that justifies connecting Google at all.

- **Touch:** new tab in `tab-config.ts` + component; new engine read endpoint over the
  persisted series (persistence already exists).
- **Verify:** the tab shows real queries, positions and clicks.
- **Free.**

### Slice 4 — Close the loop: LEARN in the UI (~1.5 h)

`/learn/outcome` already computes before/after position and click deltas. No screen.

- **Touch:** proxy route + panel on the slice-3 tab.
- **Verify:** pick an action date, see whether positions moved.
- **Free.**

### Slice 5 — The approval queue (~2 h)

ADR-0002 promises *"it proposes, you approve"*. `/act/proposals` and
`/act/proposals/{id}/{status}` exist; there is **no approval screen**, so the central
safety guarantee has no surface. Add IndexNow submission in the same slice — one button
over `/act/indexnow`.

- **Verify:** a proposal can be approved and rejected from the browser.
- **Free.** IndexNow is an open protocol (Bing, Yandex, Naver, Seznam, Yep).

### Slice S — Clean up the i18n / SiteTool debt (~1.5–2 h)

Lettered, not numbered, on purpose: this is **remediation, not progress**. Slice 1 is still
what turns a library into a product. Do this one when the debt is in the way, or first if
you would rather start from a clean base — the two are independent.

**How this was found.** Adding two comment lines to `SiteTool.tsx` and `i18n.tsx` was
rejected by the pre-commit hook (Gentleman Guardian Angel). **The hook reviews the whole
file, not the diff.** So any edit to a file, however small, pulls in every pre-existing
defect that file carries. Worth knowing before you touch either of these: a one-line change
is not a one-line review.

Two findings, and they are **not** the same kind of problem:

**1. Live defect — `i18n.tsx:474`, unstable context value.** This is not dead code. Every
tab in the dashboard consumes `i18n`. The provider returns a fresh object literal on every
render, so `t` is a new reference each time. Anything that lists `t` as a dependency
refires. In `SiteTool` that means toggling the language — or the `localStorage` restore at
`i18n.tsx:440` when the saved language is `en` — refetches both `/api/cms/audit` and
`/api/cms/pages`. There is no cancellation, so two in-flight requests can land out of
order and the **older response wins**: stale data that looks fresh, in a panel whose job is
to show the current state of a live site. The same instability affects every other consumer
of `t`; `SiteTool` is just where it produces a visible bug today.

Fix: memoize the context value and keep `t` stable. Do this **regardless** of what happens
to `SiteTool` — it is a production defect in a shared provider.

**2. Dead-code debt — `SiteTool.tsx`, nullable fields not declared.** `set()` writes `null`
into fields typed as non-nullable. It does not crash today only because every read site
defends itself (`form.h1 ?? ""` and similar). That is luck, not types. But the component is
unreachable, so **fixing it may be wasted work** — resolve slice 6 first. If the tab is
being deleted, this evaporates.

Also flagged, non-blocking: an assertion over a `false | string | null` expression at
`i18n.tsx:440`, an O(n²) `reduce`-with-spread at `i18n.tsx:403`, and a `setTimeout` without
cleanup at `SiteTool.tsx:262`.

**Acceptance condition — write this into the commit, not just the plan: the hook must pass
without `--no-verify`.** The point of this slice is to clear the debt, and bypassing the
gate that found it would leave the repo in exactly the state that made the debt invisible.
If the hook still refuses, the work is not finished.

- **Verify:** `git commit` succeeds with the hook enabled; `npx tsc --noEmit` stays clean;
  toggling the language does not refire the CMS requests.
- **Free.**

### Slice 6 — Resolve the dead code (~1 h)

Wire `SiteTool.tsx` into `tab-config.ts`, or delete it and its `site.*` i18n block.
Leaving it dead is the only option that costs something every time somebody reads the
repo — and being read is the point.

Decide reading 3 versus readings 1 and 2 first (§1).

### Slice 7 — Resolve `serpapi_key` (~1–2 h)

Write `providers/serpapi.py` behind the existing market port, or remove the setting. A
second adapter is the cheapest possible demonstration that the hexagonal claim is real.

---

## 6. The cut line for a presentable v1

**In** — everything a stranger meets in the first ten minutes:

- Gaps 1, 2, 3, 5 fixed: README starts it, one honest status, copy that matches the code.
- Slices 0–4: the loop visible end to end in the browser.
- Slice 6: no dead code shipped.
- The **live half of slice S** — the `i18n.tsx:474` context fix. It is a production defect
  in a provider every tab consumes, and it is cheap. The `SiteTool` typing half follows
  slice 6 and only if the tab survives.

**Out, deliberately** — say so rather than leaving it ambiguous:

- **Paid providers.** DataForSEO and Anthropic buy keyword discovery and competitor
  analysis. They widen the product; they are not the loop. `docs/API-LIMITS.md` has the
  detail.
- **A hosted public demo.** Needs an account and a deploy, and delivers nothing for the
  author's own SEO analysis.
- **Slice 5 (approval queue)** — the guardrail matters, but only once someone is acting
  on a real site. v1.1.
- **Slice 7 (SerpApi)** — nice demonstration, no user-visible value. v1.1.
- **A WordPress `CMSPort` adapter.** Only after the CMS direction is settled.
- **Dependabot PR #9** (Next 15.5.18 → 15.5.21, open since 2026-07-28). Independent of
  this plan; merge whenever.

v1 is roughly **11 hours of slices plus 3 hours of documentation**. In 1–2 hour sittings,
that is eight to ten sessions.
