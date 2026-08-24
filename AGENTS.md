# AceleraSEO — Coding Standards

Review rules for staged changes. A finding is only reportable when it points at a
concrete line in the diff and states the failure it causes. Style preferences that
the linters already own are not findings.

## Repository Layout

| Path | Stack |
|---|---|
| `apps/engine` | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, APScheduler |
| `apps/dashboard` | Next.js 15, React 19, TypeScript 5 |

The engine implements a Sense → Decide → Act → Learn loop over the project's own
Google Search Console and GA4 data.

## Hard Rules — Both Stacks

- Never commit secrets, API keys, OAuth client secrets, refresh tokens, or service
  account JSON. Credentials load from environment or `.env`, which stays untracked.
- Never hardcode a property ID, site URL, customer identifier, or absolute local
  path. These are configuration.
- No `TODO`/`FIXME` without an issue reference.
- No commented-out code blocks. Delete them; git remembers.
- Public-facing strings (UI copy, API error messages, log lines) are English.

## Python — `apps/engine`

- Target Python 3.12. Ruff governs formatting with `line-length = 100`; do not
  report anything Ruff would fix.
- Full type annotations on every public function and method. `mypy` must pass.
- Validate all external input through Pydantic models. Never trust a raw dict from
  a Google API response.
- Never bare `except:` or `except Exception:` without re-raising or logging with
  context. Swallowing an exception from a quota-limited API hides real failures.
- Every call to Google Search Console, GA4, or Anthropic must have an explicit
  timeout and handle rate limiting. See `docs/API-LIMITS.md`.
- No blocking I/O inside `async def`. Use `httpx.AsyncClient`, not `requests`.
- SQLAlchemy 2.0 style only: `select()` constructs, typed `Mapped[...]` columns.
  No legacy `Query` API.
- Imports resolve from `src` (`pythonpath = ["src"]`). Tests live in
  `apps/engine/tests`. Live browser tests carry the `render` marker.

## TypeScript / React — `apps/dashboard`

- Strict TypeScript. No `any`, no `@ts-ignore`, no non-null assertion (`!`) to
  silence the compiler. Narrow the type instead.
- Server Components by default. Add `"use client"` only when the component needs
  state, effects, or browser APIs, and keep it at the leaf.
- Never leak a server-side secret into a Client Component or into
  `NEXT_PUBLIC_*`.
- No `useEffect` for data fetching in Server Components. Fetch on the server.
- Every list render needs a stable `key`. Never the array index when the list can
  reorder.
- Handle the loading and error states of every async boundary. A silent failure in
  the dashboard means the operator sees stale SEO data and does not know it.

## Review Severity

| Level | Meaning |
|---|---|
| BLOCKER | Leaked credential, data loss, unhandled failure on an external API call, or a type hole that will crash at runtime |
| WARNING | Correctness risk that needs a decision but does not break the build |
| SUGGESTION | Everything else. Never blocks a commit. |

When uncertain whether a finding is real, downgrade it rather than blocking the
commit.
