# Session handoff — AceleraSEO

## Session 2026-09-15 (Block A, 07:10–12:00) — latest

**Read this section first.** Everything below it is the 2026-05-31 snapshot.

### Where things stand

- **`main` = `3a34584`.**
  - Merged today: #9 (`next` 15.5.24), #19 (dead SiteTool deleted), #18 (Spanish settings labels), #20 (write guards, loopback binding, required token), #21 (audit SSRF protection).
- **Open, rebased onto `3a34584`, CI green, not merged:**
  - #15 Connect Google, head `27dff35`, base `main`
  - #16 SENSE honest failures, head `8def26c`, base `feat/connect-google`
  - #17 SENSE panel, head `d52d699`, base `feat/sense-run-engine`

  **The only blocker is a real Google consent test.** The merge map and follow-ups are in the comment on #15.
- **The engine now requires `ENGINE_API_TOKEN`.** Without it, write and paid endpoints answer 503 and startup logs how to set it. The dashboard must send the same value (`X-Engine-Token`, server-side). A token was generated into the local `.env`.
- **The engine is published on `127.0.0.1:8000` only.**

### Running right now (left up for the consent test)

- **Engine:** Docker `aceleraseo-engine`, started with `main`'s compose file (loopback, `.env` with the token). Its image was built from a local, **unpushed** merge of `main` + #15/#16/#17: commit `20a207d` in worktree `.claude/worktrees/consent-test`, so `/auth/google/*` exists. That tree equals the #17 head `d52d699` except for #16's test-fixture token fix and one removed unused constant, so the code under test is the code up for review.
- **Dashboard:** `next start -H 127.0.0.1 -p 3000` from the same worktree, with `ENGINE_API_TOKEN` read from `.env`.
- **To return to plain `main`:** stop port 3000, then run `docker compose up -d --build` from the main checkout.

### Consent test (for Josep)

1. **`.env`'s Google OAuth client is a placeholder, not a real client.** The id is 19 characters and lacks `.apps.googleusercontent.com`, and `GSC_SITE_URL` is `sc-domain:example.com`. In Google Cloud Console:
   - create a Web OAuth client with redirect URI `http://localhost:8000/auth/google/callback`;
   - enable the Search Console API and the Analytics Data API;
   - add yourself as a test user.
2. Open `http://localhost:3000/?tab=settings`, paste the real client ID and secret, and click **Guardar ajustes**.
3. Click **Conectar Google** and give consent. Success: back on Settings with "✓ Google conectado…" and "● Conectado".
4. Then merge #15, retarget #16 to `main` and merge it, then retarget #17 to `main` and merge it.

### Follow-ups not yet filed as issues

The repo has no YAML Issue Forms (`.github/ISSUE_TEMPLATE`), and the issue workflow requires them, so these were not filed. They come from the review of the rebased stack; line numbers are on the PR heads above.

1. **"Engine offline" shows as "Not connected" (#15).** `apps/engine/src/aceleraseo/infrastructure/google/oauth.py:182`: `except GoogleAuthError` also catches `TransportError`, so a network outage makes the UI say to reconnect. `sense_run` already handles the same error as a 502.
2. **An auth failure mid-collection can still return a raw 500 (#16).** `apps/engine/src/aceleraseo/interfaces/api/app.py:211-257`: a `RefreshError` raised during `use_case.execute` escapes the second `try`. It should map to 401 "Reconnect from Settings".
3. **A crafted `?reason=` breaks the error message (#15).** `apps/dashboard/src/components/SettingsTool.tsx:98`: `GOOGLE_ERROR_KEYS[reason]` on a plain object, so `?reason=constructor` finds `Object` and renders nothing. `Object.hasOwn` or a `Map` fixes it.
4. **A disk error shows the wrong message (#15).** `apps/engine/src/aceleraseo/interfaces/api/app.py:144`: in the OAuth callback, `except Exception` also catches an `OSError` from `save_credentials`, and the user is told to check the OAuth client.

### Decisions still open for Josep

- **Rendering on self-hosted engines:** whether `render=True` should also be refused there. It is refused in demo mode because Playwright cannot intercept redirect hops or WebSockets.

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
