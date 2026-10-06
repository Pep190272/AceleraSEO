# First-party conversions from WordPress: implementation plan

- Date: 2026-10-06
- Base: `main` @ `1cc55ae`
- Branch: `feat/wp-first-party-conversions`
- Replaces: GA4 as the only conversion source (`infrastructure/google/ga4_adapter.py`)
- Status: PR A (provider, settings, `/sense/run`) merged; PR B in review on
  `feat/conversions-in-rankings` (engine) and `feat/conversions-in-rankings-dashboard`
  (Rankings tab)

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
1. Table `conversion_signals` (site, source, path, type, window end, window days, count),
   unique on site + source + path + type + window end. Saving a collection replaces that
   day's rows for the site and source in one transaction: re-running is idempotent and a
   path that dropped out does not linger. An empty collection stores one zero marker row
   (empty path and type, which no source can produce) so it still supersedes the last one.
   WordPress rows of a type other than `form`, `whatsapp` or `phone` are dropped and counted
   in the log, and the endpoint's `to` is capped at the engine's today.
2. Add conversions to `GET /sense/rankings` rows, joined on the normalised path.
3. The Rankings tab gets a conversions column, and the "conversions are not collected" line
   is shown only when the source is `none`.

Decisions taken in PR B:

| # | Decision | Why |
|---|---|---|
| D7 | A source may implement `ConversionRowsProvider.fetch_conversion_rows(days)` next to the `AnalyticsProvider` port; WordPress does. A source without it (GA4) is persisted from its per-page totals as type `ga4_key_event`, with today as the window end | The port stays compatible; GA4 keeps working and its counts are labelled for what they are |
| D8 | Snapshots are read one at a time: the Rankings tab shows the latest collection of the configured source, never a sum of collections | Collection windows overlap, so a sum would double count. Filtering by source keeps GA4 counts from showing under a WordPress label after a switch. The snapshot window ships as `conversions_window` |
| D9 | A ranking row is per query, conversions are per page. Each row gets the conversions (every type) of the query's top page: most clicks, then impressions, in the rankings window. The row names it in `top_page` | It is the page the query actually sends people to. Splitting a page's conversions across its queries would invent an attribution the data does not have, so queries sharing a page show the same count |
| D10 | `conversions` is `null` when the source is `none` or nothing was collected; a page with no conversions is `0` | A missing number and a real zero must look different |
| D11 | `normalize_path` moves to `domain/paths.py` and percent-decodes first; the GSC join and both sources use it | GSC sends `%C3%B1`, the site may send `ñ`: they are the same page |

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
| Anyone can make the site record a conversion on a made-up path (no rate limit by design) | Paths are untrusted text: rows with an implausible path (over 255 characters, no leading `/`, whitespace, control characters or backslashes) are dropped and counted in the log; the Rankings join attributes conversions only to pages Search Console reports, so a made-up path is stored but never shown, and the dashboard never renders a path as HTML or a link |
| Low volume makes the column look broken | A real zero is shown as `0` with a source label, never as an empty cell |
