# Session handoff — AceleraSEO

Snapshot of where the project stands, so the next session starts with full context.
Last updated: 2026-05-29.

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

## Milestones — ALL DONE (M0–M6) + extras

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
- **Discovery is untested against a real LLM call** — the parser + use case are unit-tested
  with fakes, and the demo guard (422) is verified, but a real Anthropic discovery run has
  NOT been done yet. First task to validate in Private mode.

## Next session — suggested order

1. **Validate discovery for real:** run Private stack, paste Anthropic key in Settings,
   try "Descubrir palabras de mi nicho" with a real business → confirm real keywords come back.
2. **Deploy the hosted demo** to a VPS / Fly.io / Railway with `DEMO_MODE=true` (needs the
   user's account — agent can't deploy).
3. Optional: Google OAuth flow in the UI → unlocks SENSE/ACT/LEARN panels (currently engine-
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
