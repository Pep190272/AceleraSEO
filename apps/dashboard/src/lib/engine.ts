// Single source of truth for talking to the engine. Server-side only:
// ENGINE_URL is never bundled into client code, so the engine stays private.

const ENGINE_URL = process.env.ENGINE_URL ?? "http://localhost:8000";

export async function engineFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${ENGINE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    // The engine data is request-specific; never cache it.
    cache: "no-store",
  });
  const text = await res.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { error: text || "Non-JSON response from engine" };
  }
  return { ok: res.ok, status: res.status, body };
}
