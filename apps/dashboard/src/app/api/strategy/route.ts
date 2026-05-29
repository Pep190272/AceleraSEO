import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /strategy/preview. Keeps the engine URL off
// the client and avoids CORS. The browser only ever talks to this Next route.
export async function POST(req: Request) {
  const payload = await req.json();
  const { ok, status, body } = await engineFetch("/strategy/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
