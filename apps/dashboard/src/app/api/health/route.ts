import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Lets the UI show whether the engine is reachable.
export async function GET() {
  try {
    const { ok, body } = await engineFetch("/health");
    return NextResponse.json({ online: ok, engine: body });
  } catch {
    return NextResponse.json({ online: false }, { status: 200 });
  }
}
