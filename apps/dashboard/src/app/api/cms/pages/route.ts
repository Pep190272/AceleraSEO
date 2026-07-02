import { NextResponse } from "next/server";

import { engineFetch } from "@/lib/engine";

// Server-side proxy for the engine's /cms/pages endpoints.
// Noor API key stays server-side — ENGINE_URL is never exposed to the client.

export async function GET() {
  const { ok, status, body } = await engineFetch("/cms/pages");
  return NextResponse.json(body, { status: ok ? 200 : status });
}

export async function PUT(req: Request) {
  const payload = await req.json();
  const { ok, status, body } = await engineFetch("/cms/pages", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return NextResponse.json(body, { status: ok ? 200 : status });
}
