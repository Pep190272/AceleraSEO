import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// A SENSE run keeps going on the engine after the dashboard stops waiting, so a
// timeout here means "not finished yet", not "failed" or "unreachable".
const STILL_RUNNING =
  "The collection is taking longer than the dashboard waits. It is most likely still " +
  "running on the engine and will save its data when it finishes, but this page cannot " +
  "show the counts for this run.";

// Server-side proxy to the engine's POST /sense/run. Fixed 90-day window for
// now — matches the default the engine itself uses when no query is passed.
export async function POST() {
  const { ok, status, body, timedOut } = await engineFetch("/sense/run?days=90", {
    method: "POST",
  });
  if (timedOut) {
    return NextResponse.json({ error: STILL_RUNNING }, { status: 504 });
  }
  return NextResponse.json(body, { status: ok ? 200 : status });
}
