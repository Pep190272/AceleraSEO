"use client";

import React, { useState } from "react";

import { useT } from "@/lib/i18n";
import { useScrollIntoView } from "@/lib/hooks/useScrollIntoView";
import type { Competitor, CompetitorResult, RankedKeyword } from "@/lib/types/api";

export default function CompetitorTool() {
  const { t, lang } = useT();
  const [domain, setDomain] = useState("");
  const [location, setLocation] = useState("");
  const [result, setResult] = useState<CompetitorResult | null>(null);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { ref: resultRef, trigger: scrollToResult } = useScrollIntoView();

  async function run() {
    if (!domain.trim()) {
      setError(t("comp.error.nodomain"));
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setExpandedDomain(null);
    try {
      const res = await fetch("/api/competitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain.trim(), location, language: lang }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Engine error");
      setResult(data);
      scrollToResult();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function toggleExpand(d: string) {
    setExpandedDomain((prev) => (prev === d ? null : d));
  }

  return (
    <div className="panel">
      <p className="lead">{t("comp.lead")}</p>

      <div className="field">
        <label>{t("comp.domain.label")}</label>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder={t("comp.domain.ph")}
        />
      </div>

      <div className="field">
        <label>{t("comp.location.label")}</label>
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder={t("comp.location.ph")}
        />
      </div>

      <button className="primary" onClick={run} disabled={loading}>
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
                            onClick={() => toggleExpand(c.domain)}
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
