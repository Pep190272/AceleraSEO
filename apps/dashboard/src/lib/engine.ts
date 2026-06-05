// Single source of truth for talking to the engine. Server-side only:
// ENGINE_URL is never bundled into client code, so the engine stays private.

const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";
const ENGINE_TIMEOUT_MS = Number(process.env.ENGINE_TIMEOUT_MS ?? 60_000);

export async function engineFetch(path: string, init?: RequestInit) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ENGINE_TIMEOUT_MS);

  // Only send Content-Type when there is a body; GET and bodyless calls must
  // not include it (RFC 7231 §3.3 — Content-Type is a representation header).
  const contentTypeHeader: Record<string, string> =
    init?.body !== undefined ? { "Content-Type": "application/json" } : {};

  try {
    const res = await fetch(`${ENGINE_URL}${path}`, {
      ...init,
      headers: { ...contentTypeHeader, ...(init?.headers ?? {}) },
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
    return { ok: res.ok, status: res.status, body };
  } catch {
    // Network errors (ECONNREFUSED, DNS failure, timeout/abort) must not
    // surface as unhandled 500s. Return a stable 503 shape instead.
    return {
      ok: false,
      status: 503,
      body: { error: "Engine unreachable" },
    } as const;
  } finally {
    clearTimeout(timer);
  }
}
