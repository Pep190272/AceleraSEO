import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Lets the UI show whether the engine is reachable.
// NOTE: always returns HTTP 200 — the engine's availability is encoded in the
// `online` boolean so the client can display status without treating it as a
// fetch error. This intentionally does not use proxyToEngine.
export async function GET() {
  try {
    const { ok, body } = await engineFetch("/health");
    return NextResponse.json({ online: ok, engine: body });
  } catch {
    return NextResponse.json({ online: false }, { status: 200 });
  }
}
