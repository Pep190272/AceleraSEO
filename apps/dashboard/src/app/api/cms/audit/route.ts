import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's GET /cms/audit.
// Noor API key stays server-side — ENGINE_URL is never exposed to the client.
export async function GET() {
  const { ok, status, body } = await engineFetch("/cms/audit");
  return NextResponse.json(body, { status: ok ? 200 : status });
}
