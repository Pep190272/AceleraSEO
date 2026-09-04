# Roadmap

Phased so each milestone is independently useful and self-hostable.

> **This file is the single source of truth for project status.** Other documents describe
> plans or history and must not restate status. Delivery plan: [PLAN.md](./PLAN.md).
> Why the status was rewritten: [ADR-0003](./adr/0003-pause-and-resume.md).

## Status — as of 2026-09-04

A milestone counts as **done** only when a user can reach it **through the UI**. Code that
exists but is callable only with `curl` is *engine-only*, not done. That test is what a
public repo is judged by, and by it the picture is:

| Milestone | Engine | Reachable in the UI | Status |
|---|---|---|---|
| M0 Scaffold & design | ✅ | n/a | **done** |
| M1 SENSE | ✅ | ❌ no OAuth button, no run control | **engine-only** |
| M2 Crawler / audit | ✅ | ✅ Audit tab | **done** (minus Core Web Vitals, never implemented) |
| M2.5 JS-rendering crawl | ✅ | ✅ via `?render=true` | **done** |
| M3 DECIDE | ✅ | ✅ Strategy + Competitors tabs | **done** |
| M4 ACT | ✅ | ❌ no IndexNow control, no approval queue | **engine-only** |
| M5 LEARN | ✅ | ❌ no screen | **engine-only** |
| M6 Docker self-host | ✅ | ⚠️ works, but the README does not say how | **partial** |

Also shipped outside the milestone list: the Next.js dashboard, UI-configured settings
with a demo-mode guard, niche keyword discovery, Spanish/English i18n, LLM key
verification, competitor-by-domain analysis, and a Noor CMS adapter (built, **not wired
into the UI**).

Closing the three *engine-only* rows is slices 1–5 of [PLAN.md](./PLAN.md).

---

## M0 — Scaffold & design ✅
- Repo, license, docs, architecture, verified API-limits research.
- `.env.example`, hexagonal skeleton.

## M1 — SENSE (read-only value, zero risk)
- Google OAuth (GSC + GA4 read scopes).
- `gsc_adapter`: pull 16 months of query/page performance.
- `ga4_adapter`: pull conversions/revenue per landing page.
- Persist as time-series.
- Dashboard: "what's ranking, what's converting, what's slipping."
- **Outcome:** already more actionable than a raw Ahrefs export — it joins rank + money.

## M2 — Built-in technical crawler
- Local crawler: status codes, Core Web Vitals proxies, schema, internal links, meta.
- Severity-tagged issues with cited rules.
- **Outcome:** Screaming Frog–class audit, no page limits, self-hosted.

## M3 — DECIDE (the brain)
- `BusinessProfile` classifier.
- Winnable-keyword scoring (`intent × volume ÷ difficulty × authority_gap`).
- Market data adapters (DataForSEO / SerpApi).
- LLM port → explained, prioritized `ActionPlan`.
- **Outcome:** the differentiator — strategy, not data dumps.

## M4 — ACT (guardrailed)
- IndexNow adapter (instant Bing/Yandex/etc on publish).
- URL Inspection monitor + "not indexed by Google after N days" alerts.
- Proposal queue + human approval UI (`AUTONOMY_MODE=none`).
- **Outcome:** closes the publish→index path safely.

## M5 — LEARN (the loop)
- Outcome measurement: did position/conversion move after each action?
- Strategy weight adjustment from real results.
- Scheduler runs the full cycle.
- **Outcome:** the autonomous agent is complete.

## M6 — Polish & community
- Docker Compose one-command self-host.
- Provider plugins (Ollama, alt market APIs).
- Docs site, contribution guide.
