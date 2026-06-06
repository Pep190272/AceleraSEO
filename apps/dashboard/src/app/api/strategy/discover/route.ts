import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's /strategy/discover (describe-your-niche).
export async function POST(req: Request) {
  const payload = await req.json();

  if (
    payload === null ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    return badRequest("Request body must be a JSON object");
  }

  return proxyToEngine("/strategy/discover", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
