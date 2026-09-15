import { proxyToEngine } from "@/lib/route-helpers";

// Whether Google OAuth is configured and a usable token is cached.
// The engine answers with booleans only; no token or secret passes through here.
export async function GET() {
  return proxyToEngine("/auth/google/status");
}
