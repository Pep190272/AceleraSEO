import { badRequest, proxyToEngine } from "@/lib/route-helpers";

// Same bounds the engine enforces on GET /sense/rankings.
const BOUNDS = {
  days: { min: 1, max: 240 },
  limit: { min: 1, max: 500 },
  min_impressions: { min: 0, max: 10000 },
} as const;

// What ranks and what is slipping, read back from the collected Search Console
// rows. Only `days`, `limit` and `min_impressions` reach the engine, and only as
// integers within the engine's own bounds; anything else in the query string is dropped.
export async function GET(req: Request) {
  const incoming = new URL(req.url).searchParams;
  const forwarded = new URLSearchParams();
  for (const name of ["days", "limit", "min_impressions"] as const) {
    const raw = incoming.get(name);
    if (raw === null) continue;
    const { min, max } = BOUNDS[name];
    if (!/^\d{1,5}$/.test(raw) || Number(raw) < min || Number(raw) > max) {
      return badRequest(`${name} must be an integer between ${min} and ${max}`);
    }
    forwarded.set(name, String(Number(raw)));
  }
  const query = forwarded.toString();
  return proxyToEngine(`/sense/rankings${query ? `?${query}` : ""}`);
}
