// Typed client for calling the dashboard's own /api/* routes from client
// components. Keeps ENGINE_URL and server secrets out of this module — those
// live in lib/engine.ts (server-only). This file is intentionally
// self-contained so it can ship as an independent PR slice.

/** Server error envelope shape returned by all /api/* routes. */
type ApiErrorEnvelope = {
  error?: string;
  detail?: unknown;
};

/**
 * Reads the server error envelope `{ error?, detail? }` and returns a
 * human-readable display message.
 *
 * Resolution order:
 *   1. `error` string from the envelope
 *   2. `detail` if it is a plain string
 *   3. Fallback: "Unexpected error"
 */
export function extractApiError(body: unknown): string {
  const envelope = body as ApiErrorEnvelope;
  if (typeof envelope?.error === "string" && envelope.error) {
    return envelope.error;
  }
  if (typeof envelope?.detail === "string" && envelope.detail) {
    return envelope.detail;
  }
  return "Unexpected error";
}

/**
 * Thin fetch wrapper for the dashboard's own /api/* routes.
 *
 * - Always sends `Content-Type: application/json` when a body is present.
 * - On non-2xx responses, throws an Error with the normalized envelope message.
 * - On network failure, re-throws the underlying error unchanged so callers can
 *   distinguish network errors from API errors if needed.
 *
 * @param path   Absolute path relative to the Next.js origin, e.g. "/api/audit"
 * @param init   Standard `RequestInit` — set `body` to a JSON-serialized string
 * @returns      Parsed JSON body typed as `T`
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const contentTypeHeader: Record<string, string> =
    init?.body !== undefined ? { "Content-Type": "application/json" } : {};

  const res = await fetch(path, {
    ...init,
    headers: { ...contentTypeHeader, ...(init?.headers ?? {}) },
  });

  const text = await res.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { error: text || "Non-JSON response" };
  }

  if (!res.ok) {
    throw new Error(extractApiError(body));
  }

  return body as T;
}
