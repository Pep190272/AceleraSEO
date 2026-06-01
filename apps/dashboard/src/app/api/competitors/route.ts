import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /competitors/analyze.
// DataForSEO credentials stay server-side — ENGINE_URL is never exposed to the client.
export async function POST(req: Request) {
  const payload = await req.json();
  const { ok, status, body } = await engineFetch("/competitors/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
