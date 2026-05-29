import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /strategy/discover (describe-your-niche).
export async function POST(req: Request) {
  const payload = await req.json();
  const { ok, status, body } = await engineFetch("/strategy/discover", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
