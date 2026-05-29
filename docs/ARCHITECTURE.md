# AceleraSEO — Architecture

## 1. Mental model: a closed-loop autonomous agent

AceleraSEO is not a reporting tool. It is a **Sense → Decide → Act → Learn** agent applied to SEO.

```
            ┌──────────────────────────────────────────────────┐
            │                                                  │
            ▼                                                  │
   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
   │     SENSE       │──▶│     DECIDE      │──▶│      ACT        │──▶│     LEARN       │
   │                 │   │                 │   │                 │   │                 │
   │ GSC rankings    │   │ Classify biz    │   │ IndexNow push   │   │ Re-read GSC/GA4 │
   │ GA4 conversions │   │ Pick winnable   │   │ Index monitor   │   │ Did it work?    │
   │ Tech crawl      │   │ keywords        │   │ On-page recs    │   │ Adjust strategy │
   │ Market APIs     │   │ Prioritize plan │   │ (human-approved)│   │ Feed back ──────┼──┘
   └─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘
```

The **LEARN** output feeds back into **DECIDE** — that loop is the whole product. Ahrefs/Semrush stop at SENSE.

## 2. Style: Hexagonal (Ports & Adapters)

Why: the data sources (Google, DataForSEO, SerpApi, the LLM) are **interchangeable details**, not the core. The core is the strategy engine. Hexagonal keeps the brain pure and the integrations swappable — so a user can plug Ollama instead of Claude, or SerpApi instead of DataForSEO, without touching domain logic.

```
apps/engine/src/aceleraseo/
├── domain/              # Pure business logic. No I/O, no frameworks.
│   ├── models.py        #   Site, Keyword, RankingSignal, BusinessProfile, ActionPlan
│   ├── strategy.py      #   The brain: classification + keyword scoring rules
│   └── ports.py         #   Interfaces (RankingProvider, MarketProvider, LLMPort, Indexer...)
│
├── application/         # Use cases that orchestrate the loop
│   ├── sense.py         #   collect_signals()
│   ├── decide.py        #   build_strategy()
│   ├── act.py           #   execute_plan() — respects AUTONOMY_MODE
│   └── learn.py         #   measure_outcomes()
│
├── infrastructure/      # Adapters implementing the ports
│   ├── google/          #   gsc_adapter.py, ga4_adapter.py, url_inspection_adapter.py
│   ├── providers/       #   dataforseo.py, serpapi.py, indexnow.py, crawler.py
│   ├── llm/             #   anthropic_adapter.py, ollama_adapter.py
│   └── persistence/     #   sqlalchemy repos
│
└── interfaces/          # Entry points
    ├── api/             #   FastAPI routes
    └── scheduler/       #   APScheduler / cron jobs that run the loop
```

**Dependency rule:** `interfaces → application → domain`. `infrastructure` implements `domain.ports`. Domain depends on NOTHING.

## 3. The strategy brain (domain/strategy.py)

This is the differentiator. Two stages:

### 3.1 Business classification
Inputs: domain age, current GSC authority signals, traffic level (GA4), site type heuristics (URL patterns, schema, product pages), geo signals.

Outputs a `BusinessProfile`:
- `type`: local | ecommerce | saas | blog | corporate
- `maturity`: new | growing | established
- `authority_band`: low | mid | high

### 3.2 Winnable-keyword scoring
For each candidate keyword:

```
opportunity = (intent_match × search_volume × business_value)
              ÷ (keyword_difficulty × authority_gap)
```

- A **new local site** → strategy weights geo + long-tail, filters out high-difficulty heads.
- An **established site** → weights defend (protect ranking 4–10 keywords) + expand competitive.
- The LLM (`LLMPort`) reasons over the structured candidates to produce a *prioritized, explained* `ActionPlan` — not just a sorted list. Explanation is mandatory (trust + auditability).

## 4. The autonomy guardrail (application/act.py)

`AUTONOMY_MODE` gates every write:

| Mode | Behavior |
|------|----------|
| `none` (default) | Engine only *proposes*. Human approves each action in the dashboard. |
| `limited` | Auto-applies low-risk actions (IndexNow pings, sitemap updates) within `MAX_AUTO_ACTIONS_PER_DAY`. Content/on-page still needs approval. |
| `full` | Fully autonomous. **Not recommended on production sites.** Hard caps still apply. |

Every action is logged with before/after + the reasoning that produced it → reversible + auditable.

## 5. Tech stack

| Concern | Choice | Reason |
|---------|--------|--------|
| Engine | **Python 3.12 + FastAPI** | Best ecosystem for Google API clients, data, and LLM SDKs |
| Scheduler | **APScheduler** (cron for prod) | Runs the loop on schedule (e.g. daily SENSE, weekly DECIDE) |
| DB | **SQLite → Postgres** | Zero-config local; Postgres for scale |
| ORM | **SQLAlchemy 2.0** | Mature, async-capable |
| Dashboard | **Next.js + TypeScript + Tailwind** | Fast, deployable, good DX |
| LLM | **Provider-agnostic port** (Anthropic / OpenAI / Ollama) | No lock-in; can run fully local |
| Packaging | **uv** (Python), **pnpm** (JS), **Docker Compose** | Reproducible self-host |

## 6. Data flow per cycle

1. **Scheduler** triggers `sense.collect_signals(site)`.
2. Adapters pull GSC (rankings), GA4 (conversions), crawler (tech), market APIs (volumes/SERP).
3. Signals persisted as time-series → enables LEARN deltas.
4. `decide.build_strategy()` → `BusinessProfile` + scored `ActionPlan` via LLM.
5. `act.execute_plan()` → respects `AUTONOMY_MODE`. IndexNow on new URLs. Queue proposals.
6. Next cycle, `learn.measure_outcomes()` compares new GSC/GA4 vs prior → did position/conversion improve? → adjusts weights and strategy.

## 7. What we deliberately do NOT build

- A web-scale crawler / backlink index (economically impossible — see [API-LIMITS.md](./API-LIMITS.md)).
- A Google force-indexer (against ToS — penalty risk).
- A "guaranteed rank #1" promise (dishonest; rankings compound).

See [API-LIMITS.md](./API-LIMITS.md) for the verified constraints that shaped this design.
