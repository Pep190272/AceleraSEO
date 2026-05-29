"use client";

import { useState } from "react";

import { useT } from "@/lib/i18n";

type Issue = { code: string; severity: string; url: string; message: string };
type Report = {
  pages_crawled: number;
  critical: number;
  warning: number;
  notice: number;
  issues: Issue[];
};

export default function AuditTool() {
  const { t } = useT();
  const [url, setUrl] = useState("https://example.com");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError("");
    setReport(null);
    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ startUrl: url, maxPages: 25 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Engine error");
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="field">
        <label>{t("audit.label")}</label>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://tusitio.com" />
      </div>

      <button className="primary" onClick={run} disabled={loading}>
        {loading ? t("audit.running") : t("audit.run")}
      </button>
      <p className="hint">{t("audit.hint")}</p>

      {error && <div className="error">⚠ {error}</div>}

      {report && (
        <div className="result">
          <div className="counts">
            <div className="count">
              <div className="n">{report.pages_crawled}</div>
              <div className="l">{t("audit.pages")}</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--crit)" }}>{report.critical}</div>
              <div className="l">{t("audit.critical")}</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--warn)" }}>{report.warning}</div>
              <div className="l">{t("audit.warning")}</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--notice)" }}>{report.notice}</div>
              <div className="l">{t("audit.notice")}</div>
            </div>
          </div>

          {report.issues.length === 0 ? (
            <p className="hint">{t("audit.none")}</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>{t("audit.col.sev")}</th>
                  <th>{t("audit.col.issue")}</th>
                  <th>{t("audit.col.url")}</th>
                </tr>
              </thead>
              <tbody>
                {report.issues.map((i, idx) => (
                  <tr key={idx}>
                    <td><span className={`sev ${i.severity}`}>{i.severity}</span></td>
                    <td>{i.message}</td>
                    <td style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                      {i.url.replace(/^https?:\/\//, "")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
