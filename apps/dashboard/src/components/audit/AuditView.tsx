import type { Report } from "@/lib/types/api";

export type AuditViewProps = {
  url: string;
  loading: boolean;
  error: string;
  report: Report | null;
  onUrlChange: (value: string) => void;
  onRun: () => void;
  t: (key: string) => string;
};

export default function AuditView({
  url,
  loading,
  error,
  report,
  onUrlChange,
  onRun,
  t,
}: AuditViewProps) {
  return (
    <div className="panel">
      <div className="field">
        <label>{t("audit.label")}</label>
        <input
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          placeholder="https://tusitio.com"
        />
      </div>

      <button className="primary" onClick={onRun} disabled={loading}>
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
                    <td>
                      <span className={`sev ${i.severity}`}>{i.severity}</span>
                    </td>
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
