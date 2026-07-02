import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /settings/verify-cms. Probes the Noor API
// key and connectivity without writing anything, so the Settings tab can confirm
// the connection works before the user tries to edit a page.
export async function POST() {
  const { ok, status, body } = await engineFetch("/settings/verify-cms", {
    method: "POST",
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
