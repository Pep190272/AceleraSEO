# Session handoff — AceleraSEO

## Session 2026-09-15 — latest

**Read this section first.** Everything below it is the 2026-05-31 snapshot.

### Where things stand (end of day)

- **Merged today**, all merge commits after green CI:
  - #9 `next` 15.5.24
  - #19 dead SiteTool deleted
  - #18 Spanish settings labels
  - #20 write/token guards, loopback binding, `ENGINE_API_TOKEN` required (fail-closed)
  - #21 audit SSRF protection
  - #15/#16/#17 Connect Google, SENSE honest failures, SENSE panel
  - #24 issue forms
  - #30 neutral Spanish (tú) instead of voseo
  - #31 placeholders read as "not configured", and SENSE errors name the failing ID
  - #32 free Brave competitor adapter
- **Google is connected** on the local instance, and SENSE has collected 4,811 positions for the configured Search Console property.
- **The engine requires `ENGINE_API_TOKEN`.** Without it, write and paid endpoints answer 503 and startup logs how to set it. The dashboard must send the same value (`X-Engine-Token`, server-side). The local `.env` has one.
- **The engine is published on `127.0.0.1:8000` only.**

### Running locally

- **Engine:** Docker `aceleraseo-engine` from `main` (`docker compose up -d --build`). The data volume holds the Google token, settings overrides and the ranking series; a rebuild keeps them, as verified on 2026-09-15.
- **Dashboard:** `next start -H 127.0.0.1 -p 3000` from `apps/dashboard` on `main`, with `ENGINE_URL=http://localhost:8000` and `ENGINE_API_TOKEN` from `.env`.
- **To stop:** kill the process listening on :3000, then run `docker compose down`.

### Competitors without a paid API

DataForSEO credentials in `.env` are placeholders, so `/competitors/analyze` answers 503 (shown in the tab).

Research on 2026-09-15 found no free, Terms-of-Service-clean source of **real Google** rankings:
- SerpApi and SearXNG scrape Google;
- Google Custom Search JSON API is closed to new customers and shuts down 2027-01-01;
- Bing Web Search API was retired 2025-08-11.

Brave Search API (https://brave.com/search/api/) gives $5 in free credits a month (about 1,000 queries) and forbids storing results. #32 adds a free opt-in adapter: it takes your top 10 Search Console queries and runs each one through Brave Search, which is 10 calls per analysis (about 100 analyses a month). It turns on when a real Brave key is saved in Settings and Google is connected. Its positions come from Brave's index, not Google's; traffic and volume are reported as unavailable. Results are held in memory only. `.env.example` does not list `BRAVE_API_KEY` yet.

### Open items

- **#22** (`next` 15 → 16, major): needs its own session for breaking-change review, security delta and local build.
- **#25–#28:** follow-up bugs from the review of the Google/SENSE stack.
- **#29:** decision on whether `render=true` should also be refused on self-hosted engines.

### Learned today

- **The pre-commit AI review (`gga`) is nondeterministic, and it reviews whole files.**
  - Capture its output on the first run: `git commit -F - > log 2>&1`.
  - `git rebase --continue` does **not** run it. Use `gga run --pr-mode --diff-only` to review a rebased stack.
- **"Non-empty" is not "real".** Measure the shape of a secret (length, suffix) without printing it.
- **Stale `.next/types` from an older build makes `tsc` fail** on deleted routes. Build first, then typecheck.
- **Tests that exercise `POST /settings` must patch `settings_store._OVERRIDES_PATH`.** It is read at import time, and otherwise the test writes a real `./data/settings-overrides.json`.
- **Chrome automation on the dashboard is flaky.** Screenshots time out and the first clicks after load are lost. `get_page_text` after click + wait is more reliable; stop after three tries.

---

> ⚠️ **Historical document. Do not read the status table below as current.**
> Written 2026-05-31. Its "M0–M6 ALL DONE" table counts a milestone as done when the code
> exists, which turned out to hide that SENSE, ACT and LEARN have no UI and are reachable
> only with `curl`.
>
> **Current status → [ROADMAP.md](./ROADMAP.md)** (the single source of truth).
> **What happens next → [PLAN.md](./PLAN.md).**
> **Why this was corrected → [ADR-0003](./adr/0003-pause-and-resume.md).**
>
> Kept because the sections below — verified API limits, the two run modes, how the
> Strategy tab works, and the environment gotchas — are still accurate and useful.

Snapshot of where the project stood on 2026-05-31.

## What AceleraSEO is

Open-source, self-hosted **autonomous SEO strategist** — *the expert, not another data
dashboard*. It runs a closed loop over the user's OWN Google Search Console + GA4:

```
SENSE → DECIDE → ACT → LEARN → (repeat)
```

Core thesis: Ahrefs/Semrush/Majestic sell **data** (un-replicable index moats —
Ahrefs ~$300M/yr infra, Majestic 21.7T-URL index). AceleraSEO sells **decisions**.
Backlink data = bring-your-own third-party API key, never a self-hosted web crawl.

- Repo (public, MIT): https://github.com/Pep190272/AceleraSEO  (gh account `Pep190272`)
- Local: `D:/Mis_proyectos/AceleraSEO`

## Architecture

Hexagonal (ports & adapters). Two apps in a monorepo:

- `apps/engine` — Python 3.12 / FastAPI. Domain logic is pure & testable; Google/LLM/
  market/crawler are swappable adapters behind ports. **64 tests, ruff clean.**
- `apps/dashboard` — Next.js 15 (App Router, TS, React 19), plain CSS. Talks to the
  engine only through server-side proxy routes (`src/app/api/*`) so `ENGINE_URL` stays
  private. **Spanish-default UI with ES/EN toggle.**

## Milestones as claimed on 2026-05-31 — SUPERSEDED

> ❌ **Out of date. This table means "the code was written", not "a user can reach it".**
> Three of these rows are engine-only. Current status: [ROADMAP.md](./ROADMAP.md).

| Milestone | What | Status |
|-----------|------|--------|
| M0 | Scaffold, docs, ADRs, verified API-limits research | ✅ |
| M1 SENSE | GSC + GA4 read adapters, OAuth (read-only scopes), time-series persistence | ✅ |
| M2 AUDIT | httpx+selectolax BFS crawler + pure severity-tagged audit rules | ✅ |
| M2.5 | Optional Playwright rendering crawler (same PageFetcher port) | ✅ |
| M3 DECIDE | Business classifier + winnable-keyword scoring + LLM narrative | ✅ |
| M4 ACT | Autonomy gate + IndexNow + URL-Inspection monitor + proposal queue | ✅ |
| M5 LEARN | Outcome measurement (position/clicks deltas) — loop closed | ✅ |
| M6 Docker | One-command self-host (`docker compose up`) | ✅ |
| Dashboard | Next.js UI: strategy + audit + settings tabs | ✅ |
| Settings | UI-configured secrets (no .env editing); DEMO_MODE guard | ✅ |
| Discovery | Describe-your-niche → keywords (LLM + DataForSEO enrichment) | ✅ |
| i18n | Spanish default + ES/EN toggle | ✅ |
| Key verify | Settings "Test AI connection" → validates LLM key + model, no tokens | ✅ |

## Verified hard limits (these shape the design — see docs/API-LIMITS.md)

- Google Indexing API = JobPosting/BroadcastEvent only. Never use for normal pages.
- URL Inspection API = read-only. No programmatic "request indexing" for Google.
- IndexNow = Bing/Yandex/Naver/etc. Google does NOT support it.
- GSC Search Analytics + GA4 Data API = free, read. The LEARN loop runs on these.

## Two run modes

| Mode | Command | Settings tab | Discovery works? |
|------|---------|--------------|------------------|
| **Public demo** | `docker compose -f docker-compose.demo.yml up --build` (engine has `DEMO_MODE=true`) | read-only | ❌ keyless by design — shows "needs a key" |
| **Private** | `docker compose up` (no DEMO_MODE) | editable in UI | ✅ once you paste an Anthropic key in Settings |

Demo URL when running: dashboard `http://localhost:3000`, engine `http://localhost:8000`.
**Stop it with:** `docker compose -f docker-compose.demo.yml down` (does NOT touch the
Docker engine or the user's automation containers).

## How the Strategy tab works (this caused confusion — read it)

Two modes inside the Strategy tab:
1. **"Descubrir palabras de mi nicho"** — type a business description + location → the
   LLM generates candidate keywords, DataForSEO enriches with real volume/difficulty,
   the engine ranks the winnable ones. **Needs an LLM key → only in Private mode.**
2. **"Ya tengo mis palabras"** — paste a keyword list → engine ranks them. Works keyless.

Results render BELOW the form and auto-scroll into view. Each keyword gets a plain-language
**verdict** (★ Mejor apuesta / Vale la pena / Difícil por ahora / Saltala) instead of a
raw number. The impossible high-difficulty head term sinks to the bottom — that's the point.

## Known issues / cleanup

- **npm audit:** Next bumped 15.1.6 → 15.5.18 (cleared critical/high). 2 *moderate* remain
  that only `npm audit fix --force` "fixes" by downgrading to next@9 (2020) — REJECTED.
  GitHub Dependabot may still show a stale higher count until it re-scans.
- **Discovery validated against a real LLM call (2026-05-31)** — ran the Private stack, pasted
  a real Anthropic key in Settings, and "Descubrir palabras de mi nicho" returned real keywords.
  Proof: engine logged `POST /strategy/discover 200` (the endpoint 422s without a real key and
  500s on a bad key — there is no NullLLM fallback for discovery, so a 200 is conclusive).

## Settings — "Test AI connection" (added 2026-05-31)

Pasting+saving an LLM key gave no signal it was valid; you only found out when an operation
failed. Fixed: the Settings tab has a **"Test AI connection"** button →
`POST /settings/verify-llm` → `factory.verify_llm()` calls Anthropic `models.retrieve(model)`,
which proves BOTH key auth AND model reachability **without spending generation tokens**. UI
shows green ✓ `Key valid (model)` or red ✗ with the reason (rejected key / model not available /
unreachable). Verdict clears on save.

## Next session — suggested order

1. **Deploy the hosted demo** to a VPS / Fly.io / Railway with `DEMO_MODE=true` (needs the
   user's account — agent can't deploy).
2. Optional: Google OAuth flow in the UI → unlocks SENSE/ACT/LEARN panels (currently engine-
   only via API). Market adapters (Majestic Trust Flow as authority proxy, SerpApi).

## Environment gotchas (save future debugging)

- The Bash tool runs **POSIX bash on Windows**, not PowerShell. `/tmp` there is NOT visible
  to the Read tool — write verification files under `D:/` repo paths instead.
- `pkill` in bash does NOT reach Windows processes. To free a port held by a Windows `npm
  start`: `netstat -ano | grep :PORT` → `powershell Stop-Process -Id <pid> -Force`.
- A half-failed `docker compose up -d` returns exit 0 but a service can be stuck `Created`
  (e.g. port clash). Always check `docker compose ps -a`.
- This session had a severe terminal-rendering glitch (fabricated/duplicated stdout). All
  results were verified via exit-code gates, file-writes + Read, and python JSON parsing —
  never trusting rendered text. Keep that discipline.
