import { proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's POST /sense/run. Fixed 90-day window for
// now — matches the default the engine itself uses when no query is passed.
export async function POST() {
  return proxyToEngine("/sense/run?days=90", { method: "POST" });
}
