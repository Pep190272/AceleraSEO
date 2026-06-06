import React from "react";

import type { CompetitorResult } from "@/lib/types/api";

export type CompetitorViewProps = {
  domain: string;
  location: string;
  result: CompetitorResult | null;
  expandedDomain: string | null;
  error: string;
  loading: boolean;
  resultRef: React.RefObject<HTMLDivElement | null>;
  onDomainChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onRun: () => void;
  onToggleExpand: (domain: string) => void;
  t: (key: string) => string;
};

export function CompetitorView({
  domain,
  location,
  result,
  expandedDomain,
  error,
  loading,
  resultRef,
  onDomainChange,
  onLocationChange,
  onRun,
  onToggleExpand,
  t,
}: CompetitorViewProps) {
  return (
    <div className="panel">
      <p className="lead">{t("comp.lead")}</p>

      <div className="field">
        <label>{t("comp.domain.label")}</label>
        <input
          value={domain}
          onChange={(e) => onDomainChange(e.target.value)}
          placeholder={t("comp.domain.ph")}
        />
      </div>

      <div className="field">
        <label>{t("comp.location.label")}</label>
        <input
          value={location}
          onChange={(e) => onLocationChange(e.target.value)}
          placeholder={t("comp.location.ph")}
        />
      </div>

      <button className="primary" onClick={onRun} disabled={loading}>
        {loading ? t("comp.analyzing") : t("comp.run")}
      </button>

      {error && <div className="error">⚠ {error}</div>}

      {result && (
        <div className="result" ref={resultRef}>
          <h2 className="result-title">{t("comp.res.title")}</h2>

          {result.competitors.length === 0 ? (
            <p className="hint">{t("comp.res.empty")}</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>{t("comp.col.domain")}</th>
                  <th className="opp">{t("comp.col.common")}</th>
                  <th className="opp">{t("comp.col.avgpos")}</th>
                  <th className="opp">{t("comp.col.traffic")}</th>
                  <th>{t("comp.col.keywords")}</th>
                </tr>
              </thead>
              <tbody>
                {result.competitors.map((c) => (
                  <React.Fragment key={c.domain}>
                    <tr>
                      <td>
                        <a href={`https://${c.domain}`} target="_blank" rel="noreferrer">
                          {c.domain}
                        </a>
                      </td>
                      <td className="opp">{c.common_keywords}</td>
                      <td className="opp">
                        {c.avg_position !== null ? c.avg_position.toFixed(1) : "—"}
                      </td>
                      <td className="opp">{c.organic_traffic.toLocaleString()}</td>
                      <td>
                        {c.ranked_keywords.length > 0 ? (
                          <button
                            className="link-btn"
                            onClick={() => onToggleExpand(c.domain)}
                            type="button"
                          >
                            {expandedDomain === c.domain
                              ? t("comp.kw.hide")
                              : t("comp.kw.show").replace("{n}", String(c.ranked_keywords.length))}
                          </button>
                        ) : (
                          <span style={{ color: "var(--muted)" }}>{t("comp.kw.none")}</span>
                        )}
                      </td>
                    </tr>
                    {expandedDomain === c.domain && c.ranked_keywords.length > 0 && (
                      <tr key={`${c.domain}-kw`}>
                        <td colSpan={5} style={{ padding: "0 0 0.75rem 1rem" }}>
                          <table style={{ width: "100%", fontSize: "0.85em" }}>
                            <thead>
                              <tr>
                                <th style={{ textAlign: "left" }}>{t("comp.kw.col.term")}</th>
                                <th className="opp">{t("comp.kw.col.pos")}</th>
                                <th className="opp">{t("comp.kw.col.vol")}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {c.ranked_keywords.map((kw, i) => (
                                <tr key={`${kw.term}-${i}`}>
                                  <td>{kw.term}</td>
                                  <td className="opp">{kw.position}</td>
                                  <td className="opp">{kw.search_volume.toLocaleString()}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}

          <p className="hint">{t("comp.res.hint")}</p>
        </div>
      )}
    </div>
  );
}
