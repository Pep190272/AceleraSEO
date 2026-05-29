"use client";

import { useState } from "react";

type Issue = { code: string; severity: string; url: string; message: string };
type Report = {
  pages_crawled: number;
  critical: number;
  warning: number;
  notice: number;
  issues: Issue[];
};

export default function AuditTool() {
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
        <label>Site URL to audit</label>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yoursite.com" />
      </div>

      <button className="primary" onClick={run} disabled={loading}>
        {loading ? "Crawling…" : "Run technical audit"}
      </button>
      <p className="hint">
        Crawls the site (same-host, up to 25 pages) and reports severity-tagged SEO issues. JS-heavy
        sites may need the rendering crawler — see the README.
      </p>

      {error && <div className="error">⚠ {error}</div>}

      {report && (
        <div className="result">
          <div className="counts">
            <div className="count">
              <div className="n">{report.pages_crawled}</div>
              <div className="l">pages</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--crit)" }}>{report.critical}</div>
              <div className="l">critical</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--warn)" }}>{report.warning}</div>
              <div className="l">warning</div>
            </div>
            <div className="count">
              <div className="n" style={{ color: "var(--notice)" }}>{report.notice}</div>
              <div className="l">notice</div>
            </div>
          </div>

          {report.issues.length === 0 ? (
            <p className="hint">No issues found on the crawled pages. ✓</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Issue</th>
                  <th>URL</th>
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
