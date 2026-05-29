import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Read the settings schema (secrets masked) from the engine.
export async function GET() {
  const { ok, status, body } = await engineFetch("/settings");
  return NextResponse.json(body, { status: ok ? 200 : status });
}

// Persist UI-provided config to the engine (blocked engine-side in demo mode).
export async function POST(req: Request) {
  const values = await req.json();
  const { ok, status, body } = await engineFetch("/settings", {
    method: "POST",
    body: JSON.stringify({ values }),
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
