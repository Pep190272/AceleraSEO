// Route helpers for Next.js App Router API handlers.
// Keeps individual route files thin: each tracked route collapses to ~1 line.

import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";
import type { ApiError } from "@/lib/api-types";

/**
 * Proxy a request to the engine and return a NextResponse with the same
 * status code. On engine errors the body (already a normalized { error } or
 * engine-provided JSON) is forwarded as-is so clients keep working.
 *
 * Usage example:
 *   export const POST = (req: Request) =>
 *     proxyToEngine("/strategy", { method: "POST", body: await req.text() });
 */
export async function proxyToEngine(
  path: string,
  init?: RequestInit,
): Promise<NextResponse> {
  const { ok, status, body } = await engineFetch(path, init);
  return NextResponse.json(body, { status: ok ? 200 : status });
}

/**
 * Return a 400 Bad Request response with an ApiError body.
 *
 * @param error  Human-readable error message.
 * @param detail Optional structured detail (e.g. per-field validation errors).
 */
export function badRequest(error: string, detail?: unknown): NextResponse {
  const payload: ApiError = detail !== undefined ? { error, detail } : { error };
  return NextResponse.json(payload, { status: 400 });
}
