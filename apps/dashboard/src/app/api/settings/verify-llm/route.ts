import { proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's /settings/verify-llm. Checks the saved LLM
// key against Anthropic (no tokens spent) so the Settings tab can confirm it works.
export async function POST() {
  return proxyToEngine("/settings/verify-llm", { method: "POST" });
}
