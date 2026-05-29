# Roadmap

Phased so each milestone is independently useful and self-hostable.

## M0 — Scaffold & design ✅ (current)
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
