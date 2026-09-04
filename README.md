# AceleraSEO

> The open-source **autonomous SEO strategist**. Not another data dashboard — a decision engine that senses your real rankings, decides the winnable strategy for *your* business, acts, and learns from the results.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status: Active development](https://img.shields.io/badge/status-active%20development-green.svg)](./docs/ROADMAP.md)

---

## Why this exists

Ahrefs, Semrush and friends are **data libraries**. They hand you 10,000 keywords and a difficulty number, then leave the actual SEO thinking to a human expert. They cost €100–600/month, lock your data in their cloud, and never touch your real performance signals.

**AceleraSEO is the expert, not the library.** It connects to your *own* Google Search Console and GA4, understands your business context, and runs a closed feedback loop:

```
  SENSE  →  DECIDE  →  ACT  →  LEARN  →  (repeat)
```

- **Open source** (MIT) — audit it, extend it, self-host it.
- **Bring-your-own-API-key** — pay-as-you-go for market data instead of fixed subscriptions.
- **Your data stays yours** — runs on your machine / your server.

## What it is NOT (honest scope)

We did the research so you don't chase impossible promises:

- ❌ **It does not own a web-scale backlink index.** Ahrefs spends ~$300M/year on infrastructure (456B pages, 35T backlinks). No open-source project can replicate that. For backlink data, AceleraSEO integrates third-party APIs with *your* key — it does not pretend to be a crawler of the whole web.
- ❌ **It cannot force-index normal pages in Google.** Google's Indexing API only accepts `JobPosting` / `BroadcastEvent`; the URL Inspection API is read-only. Anyone claiming "instant Google indexing for blog posts" is misusing the API (penalty risk).
- ❌ **It does not guarantee "rank #1 fast."** Ranking compounds with authority + time. What AceleraSEO *does* is pick the **battles you can win now** — collapsing time-to-impact by strategy, not magic.

## What it actually does

**Reach** says how you use it today: **UI** = a tab in the dashboard; **API** = implemented,
tested and exposed over HTTP, but with no screen yet. Giving the API-only rows a UI is
slices 1–5 of [docs/PLAN.md](./docs/PLAN.md).

| Layer | Capability | Data source | Reach |
|-------|-----------|-------------|-------|
| **SENSE** | Real ranking, clicks, impressions, position, CTR (16 months) | Google Search Console API | API |
| **SENSE** | Traffic, conversions, revenue per landing page | GA4 Data API | API |
| **SENSE** | Technical audit (schema presence, meta, headings, canonicals, broken links, thin content) | Built-in local crawler | **UI** |
| **SENSE** | Market: volumes, difficulty, competitors | DataForSEO (your key) | **UI** |
| **DECIDE** | Business classification + winnable-keyword strategy | LLM reasoning over the above | **UI** |
| **ACT** | Instant indexing on Bing/Yandex/Naver/Seznam/Yep | IndexNow protocol | API |
| **ACT** | Index status per URL, on demand | URL Inspection API (read) | API |
| **ACT** | On-page / content recommendations (human-approved) | Strategy engine | API |
| **LEARN** | Measure real outcome, adjust strategy, loop | GSC + GA4 feedback | API |

Not implemented, despite what earlier versions of this table said: **Core Web Vitals** are
not measured, index-status **monitoring and alerting** does not exist (the check is a
single on-demand call, with no scheduler), and **SerpApi** has a config field but no
adapter. Tracked in [docs/PLAN.md](./docs/PLAN.md).

## The strategy brain

The core differentiator. Given a site, it classifies the situation and adapts:

- **New site, no authority** → geo-local + low-difficulty long-tail (winnable in weeks).
- **High-traffic site** → defend rankings + expand into competitive terms.
- **E-commerce** → transactional intent, product/category optimization.
- **SaaS / blog** → informational funnel + topical authority clusters.

It ranks keywords not by raw volume but by **`intent × volume ÷ difficulty`** relative to *your current authority*.

## Safety first (autonomy guardrails)

An agent rewriting a live business site unsupervised is a liability. AceleraSEO defaults to **`AUTONOMY_MODE=none`** — it *proposes*, you *approve*. Higher autonomy levels are opt-in with hard daily caps.

## Architecture

Hexagonal (ports & adapters). See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

- `apps/engine` — Python (FastAPI) strategy engine + adapters
- `apps/dashboard` — Next.js UI
- `docs/` — architecture, ADRs, API limits research

## Quick start

Requires Docker. **No API keys needed to try it** — the strategy brain falls back to a
keyless mode and still produces a full plan.

```bash
git clone https://github.com/Pep190272/AceleraSEO.git
cd AceleraSEO
cp .env.example .env          # leave it empty to run keyless
docker compose up             # engine → http://localhost:8000  (API docs at /docs)
```

To get the dashboard as well:

```bash
docker compose -f docker-compose.demo.yml up --build
# dashboard → http://localhost:3000    engine → http://localhost:8000
```

Open http://localhost:3000, go to **Strategy**, paste a few keywords, and you get a
prioritised plan. Add your own API keys later from the **Settings** tab — no file editing.
Stop it with `docker compose down` (or `docker compose -f docker-compose.demo.yml down`).

What each optional key buys you, and what still works without it:
[docs/API-LIMITS.md](./docs/API-LIMITS.md).

## Status

**In active development.** The engine implements the full Sense → Decide → Act → Learn
loop; the dashboard currently exposes Decide and the technical audit, and the other three
stages are reachable over the API while their screens are built.

- Honest, per-milestone status: [docs/ROADMAP.md](./docs/ROADMAP.md)
- What gets built next, and in what order: [docs/PLAN.md](./docs/PLAN.md)

## License

MIT — see [LICENSE](./LICENSE).
