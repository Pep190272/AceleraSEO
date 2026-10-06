# First-party conversions from WordPress: implementation plan

- Date: 2026-10-06
- Base: `main` @ `1cc55ae`
- Branch: `feat/wp-first-party-conversions`
- Replaces: GA4 as the only conversion source (`infrastructure/google/ga4_adapter.py`)
- Status: PR A (provider, settings, `/sense/run`) in review on `feat/wp-conversions-provider`; PR B pending

## Why

GA4 needs a client-side tag and sets cookies (`_ga`, `_ga_*`). A site that publishes a
"no cookies" policy cannot add it without a consent banner. The reference site already
records its own leads server-side, so the engine should read conversions from the site
itself: no tag, no cookies, no third party.

## Scope

**In:** a second `AnalyticsProvider` that reads aggregated conversion counts from a
WordPress endpoint, a setting to choose the source, and persisting the counts so the
Rankings tab can show what converts.

**Out:** the WordPress plugin itself. It lives in the site's own repository. This
document only fixes the contract it must serve.

## Contract the site must serve

```
GET <endpoint>?days=<1..480>
X-API-Key: <key>
```

| Status | When |
|---|---|
| 200 | Valid key |
| 401 | Missing or wrong key (compared with `hash_equals`) |
| 422 | `days` out of range |

```json
{
  "from": "2026-07-08",
  "to": "2026-10-06",
  "rows": [
    {"path": "/agencia-adwords-barcelona/", "type": "form", "count": 2},
    {"path": "/", "type": "whatsapp", "count": 1}
  ]
}
```

- **What a row means:** each row is one landing path and one conversion type, with the
  count over the window.
- **Paths:** site-relative, with a leading and trailing slash, and no query string.
- **Types:** `form` and `whatsapp` exist today. `phone` is reserved for later.
- **Privacy:** aggregates only. No IPs, user agents, identifiers or form contents ever
  cross the wire.

## Decisions

| # | Decision | Why |
|---|---|---|
| D1 | New setting `conversions_source`: `none` / `ga4` / `wordpress`. It defaults to `ga4` when `ga4_property_id` is set, otherwise `none` | Existing installs keep working; GA4 becomes optional instead of hard-wired at `app.py:210-219` |
| D2 | New settings `wp_conversions_url` (full endpoint URL) and `wp_conversions_key` (secret, masked like other keys) | The engine stays site-agnostic: no namespace or path is hard-coded |
| D3 | `make_analytics(settings)` factory next to `make_cms` in `infrastructure/llm/factory.py` | Same selection pattern as the other providers |
| D4 | `WordPressConversionsProvider` modelled on the Noor adapter (`providers/noor.py:153-215`): `httpx`, `X-API-Key`, 30 s timeout, 401/422 mapped to a typed error | Proven pattern in this codebase |
| D5 | The port keeps `fetch_conversions(...) -> dict[path, float]` (sum over types) for this slice; the per-type split is persisted in the next one | Smallest change to `application/sense.py` |
| D6 | GSC pages are full URLs, the contract gives paths: join on the normalised path | One normalisation helper, tested |

## Steps

### PR A: `feat(engine)`, WordPress conversions provider
1. Add the provider, a typed error and the response model (Pydantic: never trust a raw dict).
2. Add the factory and the settings (`config.py`, `settings_store.py`); the key is masked in `GET /settings`.
3. `POST /sense/run` uses the factory. The response gains `analytics_source` and keeps `ga4_*` for compatibility. Provider errors map to readable 502/504/401 responses.
4. `SenseRunPanel` names the source and keeps the "no data" hint.
5. Tests:
   - provider against `httpx.MockTransport`: 200, 401, 422, timeout, malformed body;
   - factory selection;
   - `/sense/run` with a fake provider.
6. Docs: README, `docs/API-LIMITS.md`.

### PR B: `feat`, persist conversions and show them
1. Table `conversion_signals` (site, path, type, observed window end, count), with an idempotent upsert.
2. Add conversions per page to `GET /sense/rankings` rows, joined on the normalised path.
3. The Rankings tab gets a conversions column, and the "conversions are not collected" line goes away when a source is configured.

## Verification

| Check | How |
|---|---|
| Unit | `pytest -q`, `ruff check src`, mypy on the touched modules |
| Dashboard | `npm run build`, `npm run typecheck` (CI job) |
| End to end, local | Point `wp_conversions_url` at the site's LocalWP copy, run a collection, and see the counts in `/sense/run` and in the Rankings tab |
| Production | Only after the plugin is live on the site: one collection; the counts match the plugin's table |

## Risks

| Risk | Mitigation |
|---|---|
| The site's security plugins block unauthenticated REST routes | The route authenticates with its own key; confirm on LocalWP first |
| Page cache serves a stale JSON | The endpoint sends `Cache-Control: no-store`; the plugin side must exclude the route from caching |
| Low volume makes the column look broken | A real zero is shown as `0` with a source label, never as an empty cell |
