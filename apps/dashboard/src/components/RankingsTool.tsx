"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { GoogleStatus, RankingsReport } from "@/lib/types/api";

const WINDOWS = [7, 28, 90] as const;
type WindowDays = (typeof WINDOWS)[number];

type SettingsSummary = { fields: { key: string; is_set: boolean }[] };

type View =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "no_site_url" }
  | { kind: "ready"; report: RankingsReport; google: GoogleStatus | null };

// What ranks and what is slipping, from the Search Console rows SENSE persisted.
// Laid out as sections so the LEARN panel (slice 4) can join as one more.
export default function RankingsTool() {
  const { lang, t } = useT();
  const [days, setDays] = useState<WindowDays>(28);
  const [view, setView] = useState<View>({ kind: "loading" });

  // The fetch depends on `days` only: labels and number formats are applied at
  // render time, so a language switch re-renders the same data without a request.
  // `ignore` drops any response that lands after `days` changed or the tab unmounted.
  useEffect(() => {
    let ignore = false;
    setView({ kind: "loading" });
    Promise.allSettled([
      apiFetch<SettingsSummary>("/api/settings"),
      apiFetch<GoogleStatus>("/api/auth/google/status"),
      apiFetch<RankingsReport>(`/api/sense/rankings?days=${days}`),
    ]).then(([settings, google, rankings]) => {
      if (ignore) return;
      const siteUrlSet =
        settings.status !== "fulfilled" ||
        settings.value.fields.some((f) => f.key === "gsc_site_url" && f.is_set);
      if (!siteUrlSet) {
        setView({ kind: "no_site_url" });
      } else if (rankings.status === "rejected") {
        const reason: unknown = rankings.reason;
        setView({ kind: "error", message: reason instanceof Error ? reason.message : String(reason) });
      } else {
        setView({
          kind: "ready",
          report: rankings.value,
          google: google.status === "fulfilled" ? google.value : null,
        });
      }
    });
    return () => {
      ignore = true;
    };
  }, [days]);

  const num = (n: number) => n.toLocaleString(lang);
  const pos = (n: number) =>
    n.toLocaleString(lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  return (
    <div className="panel">
      <p className="hint" style={{ marginTop: 0 }}>{t("rank.lead")}</p>

      <div style={{ maxWidth: "16rem", marginBottom: "1rem" }}>
        <label htmlFor="rank-window">{t("rank.window")}</label>
        <select
          id="rank-window"
          className="select"
          value={days}
          onChange={(e) => {
            const next = WINDOWS.find((w) => w === Number(e.target.value));
            if (next !== undefined) setDays(next);
          }}
        >
          {WINDOWS.map((w) => (
            <option key={w} value={w}>
              {w} {t("rank.days")}
            </option>
          ))}
        </select>
      </div>

      {view.kind === "loading" && <p className="hint">{t("rank.loading")}</p>}
      {view.kind === "error" && <div className="error">⚠ {view.message}</div>}
      {view.kind === "no_site_url" && <p className="hint">{t("rank.no_site_url")}</p>}

      {view.kind === "ready" && view.report.rows.length === 0 && (
        <p className="hint">
          {view.google && !view.google.connected ? t("rank.not_connected") : t("rank.empty")}
        </p>
      )}

      {view.kind === "ready" && view.report.rows.length > 0 && (
        <div className="result">
          <p className="hint">
            {t("rank.period")} {view.report.window.start} → {view.report.window.end}
          </p>
          <table>
            <thead>
              <tr>
                <th>{t("rank.col.query")}</th>
                <th>{t("rank.col.clicks")}</th>
                <th>{t("rank.col.impressions")}</th>
                <th>{t("rank.col.position")}</th>
                <th title={t("rank.delta.hint")}>Δ</th>
              </tr>
            </thead>
            <tbody>
              {view.report.rows.map((r) => (
                <tr key={r.query}>
                  <td>{r.query}</td>
                  <td>{num(r.clicks)}</td>
                  <td>{num(r.impressions)}</td>
                  <td>{pos(r.position)}</td>
                  <td
                    style={{
                      color:
                        r.position_delta === null || r.position_delta === 0
                          ? "var(--muted)"
                          : r.position_delta > 0
                            ? "var(--warn)"
                            : "var(--accent)",
                    }}
                  >
                    {r.position_delta === null
                      ? t("rank.new")
                      : `${r.position_delta > 0 ? "+" : ""}${pos(r.position_delta)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">{t("rank.delta.hint")}</p>
        </div>
      )}

      <p className="hint">{t("rank.no_conversions")}</p>
    </div>
  );
}
