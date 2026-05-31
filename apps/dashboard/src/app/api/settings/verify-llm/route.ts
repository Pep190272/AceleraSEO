import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /settings/verify-llm. Checks the saved LLM
// key against Anthropic (no tokens spent) so the Settings tab can confirm it works.
export async function POST() {
  const { ok, status, body } = await engineFetch("/settings/verify-llm", {
    method: "POST",
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
