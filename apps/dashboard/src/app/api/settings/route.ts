import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Read the settings schema (secrets masked) from the engine.
export async function GET() {
  return proxyToEngine("/settings");
}

// Persist UI-provided config to the engine (blocked engine-side in demo mode).
export async function POST(req: Request) {
  const body = await req.json();

  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return badRequest("Request body must be a JSON object");
  }

  const { values } = body as Record<string, unknown>;
  if (values === undefined || values === null || typeof values !== "object") {
    return badRequest("values is required and must be an object");
  }

  return proxyToEngine("/settings", {
    method: "POST",
    body: JSON.stringify({ values }),
  });
}
