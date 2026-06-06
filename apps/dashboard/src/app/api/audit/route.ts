import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Server-side proxy to the engine's /audit/run.
export async function POST(req: Request) {
  const body = await req.json();
  const { startUrl, maxPages, render } = body ?? {};

  if (!startUrl || typeof startUrl !== "string") {
    return badRequest("startUrl is required and must be a string");
  }

  const params = new URLSearchParams({
    start_url: startUrl,
    max_pages: String(maxPages ?? 40),
    render: String(Boolean(render)),
  });

  return proxyToEngine(`/audit/run?${params}`, { method: "POST" });
}
