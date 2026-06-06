import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's /strategy/preview. Keeps the engine URL off
// the client and avoids CORS. The browser only ever talks to this Next route.
export async function POST(req: Request) {
  const payload = await req.json();

  if (
    payload === null ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    return badRequest("Request body must be a JSON object");
  }

  return proxyToEngine("/strategy/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
