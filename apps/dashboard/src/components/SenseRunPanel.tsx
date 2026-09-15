"use client";

import { useT } from "@/lib/i18n";
import { apiFetch } from "@/lib/api";
import { useApiCall } from "@/lib/hooks/useApiCall";
import type { GoogleStatus, SenseResult } from "@/lib/types/api";

type Props = {
  demo: boolean;
  // undefined = still checking, null = could not be checked — mirrors the
  // Google connection section above, which owns this same status fetch.
  google: GoogleStatus | null | undefined;
  siteUrlSet: boolean;
};

// "Run collection" control for SENSE (POST /sense/run). Lives directly below
// the Google connection section in Settings: SENSE needs that connection and
// the Search Console site URL, in that order, so degraded states here always
// point back up at the section that unblocks them — never a live button that
// is guaranteed to fail.
export default function SenseRunPanel({ demo, google, siteUrlSet }: Props) {
  const { t } = useT();
  const { data, loading, error, execute } = useApiCall<SenseResult>();

  function run() {
    execute(() => apiFetch<SenseResult>("/api/sense/run", { method: "POST" }));
  }

  // Google status hasn't resolved yet — the section above already shows
  // "checking"; avoid a second, possibly contradictory message here.
  if (google === undefined) return null;

  let blockedReason: string | null = null;
  if (demo) {
    blockedReason = t("set.sense.demo");
  } else if (google === null) {
    blockedReason = t("set.google.unknown");
  } else if (!google.configured) {
    blockedReason = t("set.sense.needs_google");
  } else if (!google.connected) {
    blockedReason = t("set.sense.needs_connection");
  } else if (!siteUrlSet) {
    blockedReason = t("set.sense.needs_site_url");
  }

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <h3
        style={{
          fontSize: "0.9rem",
          color: "var(--muted)",
          marginBottom: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {t("set.sense.title")}
      </h3>

      {blockedReason ? (
        <p className="hint">{blockedReason}</p>
      ) : (
        <>
          <button className="primary" onClick={run} disabled={loading}>
            {loading ? t("set.sense.running") : t("set.sense.run")}
          </button>
          <p className="hint" style={{ marginTop: "0.5rem" }}>
            {t("set.sense.hint")}
          </p>
        </>
      )}

      {error && !loading && <div className="error">⚠ {error}</div>}

      {data && !loading && (
        <div className="result">
          <p style={{ fontWeight: 600, color: "var(--accent)" }}>{t("set.sense.done")}</p>
          <div className="counts">
            <div className="count">
              <div className="n">{data.rankings_fetched}</div>
              <div className="l">{t("set.sense.rankings_fetched")}</div>
            </div>
            <div className="count">
              <div className="n">{data.rankings_new}</div>
              <div className="l">{t("set.sense.rankings_new")}</div>
            </div>
            <div className="count">
              <div className="n">{data.pages_with_conversions}</div>
              <div className="l">{t("set.sense.conversions")}</div>
            </div>
          </div>
          {!data.ga4_configured && <p className="hint">{t("set.sense.no_ga4")}</p>}
        </div>
      )}
    </div>
  );
}
