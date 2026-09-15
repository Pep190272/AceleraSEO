import { engineFetch } from "@/lib/engine";

const GOOGLE_CONSENT_ORIGIN = "https://accounts.google.com/";

// Maps an engine refusal to a reason the Settings tab knows how to explain.
function reasonFor(status: number): string {
  switch (status) {
    case 400:
      return "not_configured";
    case 403:
      return "demo";
    case 503:
      return "unreachable";
    default:
      return "failed";
  }
}

// Starts Google consent. The browser navigates here (it does not fetch it), so every
// outcome is a redirect: to Google's consent screen on success, or back to the
// Settings tab with a reason. The engine's own redirect is read server-side with
// `redirect: "manual"`, so ENGINE_URL never reaches the browser — only the Google
// URL does, and only if it really points at Google.
export async function GET() {
  const { status, headers } = await engineFetch("/auth/google/login", { redirect: "manual" });
  const location = headers.get("location");

  if (status >= 300 && status < 400 && location?.startsWith(GOOGLE_CONSENT_ORIGIN)) {
    return new Response(null, { status: 302, headers: { Location: location } });
  }

  const params = new URLSearchParams({
    tab: "settings",
    google: "error",
    reason: reasonFor(status),
  });
  // Relative Location: resolved by the browser against the dashboard origin it is
  // already on, which the server cannot reliably know behind a proxy or container.
  return new Response(null, { status: 303, headers: { Location: `/?${params}` } });
}
