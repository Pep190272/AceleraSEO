import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's /competitors/analyze.
// DataForSEO credentials stay server-side — ENGINE_URL is never exposed to the client.
export async function POST(req: Request) {
  const payload = await req.json();

  if (
    payload === null ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    return badRequest("Request body must be a JSON object");
  }

  const { domain } = payload as Record<string, unknown>;
  if (!domain || typeof domain !== "string") {
    return badRequest("domain is required and must be a string");
  }

  return proxyToEngine("/competitors/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
