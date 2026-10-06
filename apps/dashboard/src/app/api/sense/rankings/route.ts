import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Same bounds the engine enforces on GET /sense/rankings.
const LIMITS = { days: 240, limit: 500 } as const;

// What ranks and what is slipping, read back from the collected Search Console
// rows. Only `days` and `limit` reach the engine, and only as positive integers
// within the engine's own bounds; anything else in the query string is dropped.
export async function GET(req: Request) {
  const incoming = new URL(req.url).searchParams;
  const forwarded = new URLSearchParams();
  for (const name of ["days", "limit"] as const) {
    const raw = incoming.get(name);
    if (raw === null) continue;
    if (!/^\d{1,3}$/.test(raw) || Number(raw) < 1 || Number(raw) > LIMITS[name]) {
      return badRequest(`${name} must be an integer between 1 and ${LIMITS[name]}`);
    }
    forwarded.set(name, String(Number(raw)));
  }
  const query = forwarded.toString();
  return proxyToEngine(`/sense/rankings${query ? `?${query}` : ""}`);
}
