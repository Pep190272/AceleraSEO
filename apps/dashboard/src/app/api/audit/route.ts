import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy to the engine's /audit/run.
export async function POST(req: Request) {
  const { startUrl, maxPages, render } = await req.json();
  const params = new URLSearchParams({
    start_url: String(startUrl),
    max_pages: String(maxPages ?? 40),
    render: String(Boolean(render)),
  });
  const { ok, status, body } = await engineFetch(`/audit/run?${params}`, {
    method: "POST",
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
