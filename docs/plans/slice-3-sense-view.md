# Slice 3 — Show what SENSE collected: implementation plan

- Date: 2026-10-05
- Base: `main` @ `78360c6`
- Branch: `feat/slice-3-sense-view`
- Source: `docs/PLAN.md` slice 3, `docs/ROADMAP.md` M1, ADR-0003 (free stack only)

Slices 1 and 2 are merged (#15, #16, #17, #31). The engine already persists Search
Console rows (4,811 on the local instance), but nothing shows them. This slice adds the
first screen that justifies connecting Google.

## Scope

**In:** "what's ranking" and "what's slipping", both drawn from `ranking_signals`.

**Out (recorded, not hidden):** "what's converting". GA4 conversions are **not persisted**.
`CollectSignals.execute` (`application/sense.py:31-48`) counts them and throws the rows
away. Showing them needs a new table and a change to the SENSE write path, which is a
separate slice. The tab says so honestly instead of showing an empty column.

## Decisions taken (no input available before 12:00; each is reversible)

| # | Decision | Why |
|---|---|---|
| D1 | One new read, `GET /sense/rankings?days=28&limit=50` | One endpoint feeds the whole table, with nothing extra to compute in the browser. |
| D2 | Aggregate in SQL, per query, over the window: `sum(clicks)`, `sum(impressions)`, impression-weighted `avg(position)` | 90 days × thousands of rows must not cross the wire raw. |
| D3 | "Slipping" = same aggregate over the **previous** window of equal length; `position_delta = current − previous` (positive = worse) | The same comparison LEARN uses. No new concept. |
| D4 | The route is guarded by `require_token` (`_COSTLY` guard) | It returns client search data. The dashboard proxy already sends the token, so the cost is zero. Other GETs are unguarded, but there is no reason to copy that. |
| D5 | Read-back goes through a new method on `RankingRepository`, called by a small use case `ReportRankings` in `application/report.py` | PLAN §3 "ports worth adding #1"; keeps `app.py` thin. |
| D6 | New tab `rankings`, a Client Component using `useApiCall` + `apiFetch` | Matches every existing tab. A Server Component tab would be the only one of its kind. |
| D7 | Close the dashboard verification gap with a CI job, not ESLint | ESLint config is slice T, and `next lint` without config opens an interactive wizard. |
| D8 | (Follow-up) `min_impressions: Query(10, ge=0, le=10000)`: queries below it in the current window are dropped via `HAVING` before `LIMIT`; each row carries `previous_impressions`, and `position_delta` is `null` when that is below the threshold. The tab offers 0/10/50/100 | Queries with a handful of impressions showed deltas like −79.5. `0` restores the unfiltered view. |

## Steps (each one is a work-unit commit)

### 1. `ci(dashboard)`: make the dashboard verifiable (do this first)

- `.github/workflows/ci.yml`: new `dashboard` job: `npm ci`, `npm run build`, then
  `npx tsc --noEmit` (build first: stale `.next/types` breaks tsc, HANDOFF:53).
- `apps/dashboard/package.json`: add `"typecheck": "tsc --noEmit"`.
- **Gate:** this job must be green on the branch **before** any UI change lands, so the UI
  commits are checked by something other than a human.

### 2. `feat(engine)`: rankings read-back

- `infrastructure/persistence/repository.py`: `summarize_by_query(site_url, start, end,
  limit) -> list[QueryRanking]`: `select()` + `group_by(query)` + `order_by(clicks desc)`,
  typed. Annotate `session_factory` while there, because the hook reviews the whole file.
- `domain/models.py`: frozen dataclass `QueryRanking(query, clicks, impressions, position)`.
- `application/report.py`: `ReportRankings(repo).execute(site_url, today, days, limit)`
  returns the current window joined with the previous window, plus `first_observed_on` and
  `last_observed_on`.
- `interfaces/api/app.py`: `GET /sense/rankings`, `days: Query(28, ge=1, le=240)`,
  `limit: Query(50, ge=1, le=500)`. Return 400 "GSC_SITE_URL not set" (same as
  `/learn/outcome`). An empty DB returns 200 with `rows: []`, not an error.
- **Response:**

  ```json
  {"site_url": "...", "window": {"start": "...", "end": "...", "days": 28},
   "min_impressions": 10,
   "first_observed_on": "...", "last_observed_on": "...",
   "rows": [{"query": "...", "clicks": 0, "impressions": 0, "position": 0.0,
             "previous_position": null, "previous_impressions": 0,
             "position_delta": null}]}
  ```

### 3. `test(engine)`

- `tests/test_report_usecase.py`: fake repo. Cover the window maths, deltas, a query
  missing from the previous window (`null` delta), and an empty window.
- `tests/test_rankings_repository.py`: real SQLite on `tmp_path`. Check the aggregation
  and the weighted position.
- `tests/test_sense_rankings_api.py`, modelled on `test_sense_api.py`:
  - 401 without a token
  - 400 without a site URL
  - 200 with rows
  - 200 when empty
  - 422 when `days`/`limit` are out of range
- **Gotcha:** `sqlite:///:memory:` + a fresh engine per `make_session_factory` call means
  seeded data is invisible to the endpoint. Use `sqlite:///{tmp_path}/t.db`.

### 4. `feat(dashboard)`: the Rankings tab

- `src/app/api/sense/rankings/route.ts`: `GET` → `proxyToEngine("/sense/rankings?...")`,
  forwarding only validated `days`/`limit`.
- `src/lib/types/api.ts`: `RankingRow`, `RankingsReport`.
- `src/components/RankingsTool.tsx` (client):
  - **Controls:** a window selector (7 / 28 / 90 days).
  - **Table:** query, clicks, impressions, position, Δ. The key is `query`, never the index.
  - **States** (every async boundary):
    - loading
    - error (the engine message)
    - not connected / no site URL (hint pointing to Settings)
    - empty ("Run a collection in Settings")
    - data
  - A line saying conversions are not collected yet.
  - **Request race (PLAN 233-262):** ignore stale responses when `days` or `lang` changes
    (ignore flag in the effect).
- `src/lib/tab-config.ts`: add `{ id: "rankings", labelKey: "nav.rankings", component }`.
- `src/lib/i18n.tsx`: `nav.rankings` + a `rank.*` namespace in **both** `es` and `en`.
  Extend `NamespacedDict`. Neutral Spanish (tú), no voseo (#30).

### 5. `docs`

- `docs/PLAN.md` slice 3 status, `README.md` (the tab list and what the dashboard shows),
  `docs/SESSION-HANDOFF.md`. Same PR as the behaviour.

## Verification

| Check | Command | Covers |
|---|---|---|
| Engine tests | `cd apps/engine && pytest -q` | steps 2-3 |
| Engine lint | `ruff check src` | CI parity |
| Engine types | `mypy src/aceleraseo/application/report.py src/aceleraseo/infrastructure/persistence/repository.py` | AGENTS.md "mypy must pass"; not in CI, so run by hand on the touched files |
| Dashboard build | `cd apps/dashboard && npm run build` | step 4; now also in CI |
| Dashboard types | `npm run typecheck` | step 4; now also in CI |
| Pre-commit | `gga` hook on every commit, never `--no-verify` | AGENTS.md review |
| Browser | local `uvicorn` + `npm run dev` against a **seeded tmp SQLite** (no Docker rebuild, no `.env` change): every state renders, deep link `?tab=rankings` works, the language switch does not show stale data | the PLAN "Verify" line, minus real data |
| Real data | Josep opens the tab on his running stack (4,811 rows) | PLAN "Verify: the tab shows real queries, positions and clicks" |

No dashboard unit-test framework is added in this slice. Adding Vitest is a choice of
its own; build + typecheck + browser check is the honest bar for now.

## Delivery

- Budget about 400 lines per PR. Expected: CI ~30, engine + tests ~300, UI + i18n ~250.
  If the total goes over, split the UI into a stacked PR (`feat/slice-3-sense-view-ui`),
  as slice 2 did (#16/#17).
- Open a PR only when CI is green **including the new dashboard job**. Do not merge
  without Josep.

## Risks

| Risk | Mitigation |
|---|---|
| The hook reviews whole files and is nondeterministic; touching `i18n.tsx` pulls in slice T debt (`TranslationKey` ≈ `string`) and `app.py` pulls in everything | Keep the edits to those files minimal; budget time for hook findings; fix what is in scope, record the rest in PLAN slice T; never `--no-verify` |
| Building the Docker image is out of scope today, so the running stack will not show the tab | Verify against a local dev engine + seeded DB; real-data check goes to Josep |
| `GROUP BY` on a 2,048-char `query` column gets slow as the table grows | Fine at ~5k rows; index note added to PLAN; revisit when it hurts |
| The weighted average position hides per-page splits | Documented in the tab footnote; per-page drill-down is a later slice |
| Slice 4 (LEARN panel) lands on the same tab | Lay the component out as sections so LEARN is one more section |
| mypy is not in CI | Run it by hand on the touched modules; adding it to CI is a separate change |
