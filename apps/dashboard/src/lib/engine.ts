// Single source of truth for talking to the engine. Server-side only:
// ENGINE_URL is never bundled into client code, so the engine stays private.

const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";
const ENGINE_TIMEOUT_MS = Number(process.env.ENGINE_TIMEOUT_MS ?? 60_000);
// Shared secret the engine requires on write endpoints when it sets ENGINE_API_TOKEN.
const ENGINE_API_TOKEN = process.env.ENGINE_API_TOKEN ?? "";

export async function engineFetch(path: string, init?: RequestInit) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ENGINE_TIMEOUT_MS);

  // Only send Content-Type when there is a body; GET and bodyless calls must
  // not include it (RFC 7231 §3.3 — Content-Type is a representation header).
  const contentTypeHeader: Record<string, string> =
    init?.body !== undefined ? { "Content-Type": "application/json" } : {};
  const tokenHeader: Record<string, string> = ENGINE_API_TOKEN
    ? { "X-Engine-Token": ENGINE_API_TOKEN }
    : {};

  try {
    const res = await fetch(`${ENGINE_URL}${path}`, {
      ...init,
      headers: { ...contentTypeHeader, ...tokenHeader, ...(init?.headers ?? {}) },
      // The engine data is request-specific; never cache it.
      cache: "no-store",
      signal: controller.signal,
    });

    const text = await res.text();
    let body: unknown;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { error: text || "Non-JSON response from engine" };
    }
    // Headers are exposed for callers that pass `redirect: "manual"` and need the
    // engine's Location (the Google consent redirect).
    return { ok: res.ok, status: res.status, headers: res.headers, body, timedOut: false };
  } catch {
    // Our own timeout fired: the engine may still be working on the request,
    // so this must not be reported as "unreachable".
    if (controller.signal.aborted) {
      return {
        ok: false,
        status: 504,
        headers: new Headers(),
        body: { error: "Engine did not respond in time" },
        timedOut: true,
      } as const;
    }
    // Network errors (ECONNREFUSED, DNS failure, timeout/abort) must not
    // surface as unhandled 500s. Return a stable 503 shape instead.
    return {
      ok: false,
      status: 503,
      headers: new Headers(),
      body: { error: "Engine unreachable" },
      timedOut: false,
    } as const;
  } finally {
    clearTimeout(timer);
  }
}
