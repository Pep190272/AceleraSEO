# AceleraSEO

> The open-source **autonomous SEO strategist**. Not another data dashboard — a decision engine that senses your real rankings, decides the winnable strategy for *your* business, acts, and learns from the results.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status: Design](https://img.shields.io/badge/status-design-blue.svg)](./docs/ARCHITECTURE.md)

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

| Layer | Capability | Data source |
|-------|-----------|-------------|
| **SENSE** | Real ranking, clicks, impressions, position, CTR (16 months) | Google Search Console API |
| **SENSE** | Traffic, conversions, revenue per landing page | GA4 Data API |
| **SENSE** | Technical audit (Core Web Vitals, schema, crawl) | Built-in local crawler |
| **SENSE** | Market: volumes, difficulty, SERP, competitors | DataForSEO / SerpApi (your key) |
| **DECIDE** | Business classification + winnable-keyword strategy | LLM reasoning over the above |
| **ACT** | Instant indexing on Bing/Yandex/Naver/Seznam/Yep | IndexNow protocol |
| **ACT** | Index-status monitoring + alerts for Google | URL Inspection API (read) + sitemap |
| **ACT** | On-page / content recommendations (human-approved) | Strategy engine |
| **LEARN** | Measure real outcome, adjust strategy, loop | GSC + GA4 feedback |

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

## Quick start (design phase)

```bash
cp .env.example .env   # fill in your keys
# engine + dashboard setup — see docs/ARCHITECTURE.md
```

## Status

🚧 **Design phase.** This repo currently contains the architecture, the verified API-limits research, and the project scaffold. Implementation roadmap in [docs/ROADMAP.md](./docs/ROADMAP.md).

## License

MIT — see [LICENSE](./LICENSE).
