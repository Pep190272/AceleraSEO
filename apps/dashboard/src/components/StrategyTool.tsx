"use client";

import { useState } from "react";

type Scored = { term: string; opportunity: number; rationale: string };
type Action = { kind: string; target_url: string; risk: string; description: string };
type Plan = {
  profile: { type: string; maturity: string; authority_band: string; is_geo_relevant: boolean };
  executive_summary: string;
  keywords: Scored[];
  actions: Action[];
};

const SAMPLE = `fontanero, 40000, 88, commercial
fontanero urgente gracia barcelona, 210, 14, transactional
reparar fuga agua barcelona, 480, 22, transactional
precio reparacion caldera, 2900, 61, commercial`;

function parseKeywords(raw: string) {
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const [term, vol, diff, intent] = line.split(",").map((s) => s.trim());
      return {
        term,
        search_volume: Number(vol) || 0,
        difficulty: Number(diff) || 0,
        intent: intent || "informational",
      };
    });
}

export default function StrategyTool() {
  const [rankingQueries, setRankingQueries] = useState(8);
  const [isLocal, setIsLocal] = useState(true);
  const [kwText, setKwText] = useState(SAMPLE);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError("");
    setPlan(null);
    try {
      const res = await fetch("/api/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          snapshot: { ranking_query_count: Number(rankingQueries), has_local_signals: isLocal },
          keywords: parseKeywords(kwText),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Engine error");
      setPlan(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="row">
        <div>
          <label>Ranking queries (GSC authority proxy)</label>
          <input
            type="number"
            value={rankingQueries}
            onChange={(e) => setRankingQueries(Number(e.target.value))}
          />
        </div>
        <div>
          <label>Local business?</label>
          <select
            value={isLocal ? "yes" : "no"}
            onChange={(e) => setIsLocal(e.target.value === "yes")}
            style={{
              width: "100%",
              background: "var(--panel-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
              padding: "0.6rem 0.75rem",
            }}
          >
            <option value="yes">Yes (geo-relevant)</option>
            <option value="no">No</option>
          </select>
        </div>
      </div>

      <div className="field">
        <label>Candidate keywords — one per line: term, volume, difficulty, intent</label>
        <textarea value={kwText} onChange={(e) => setKwText(e.target.value)} rows={6} />
      </div>

      <button className="primary" onClick={run} disabled={loading}>
        {loading ? "Thinking…" : "Build strategy"}
      </button>
      <p className="hint">
        Runs with no API keys. The engine classifies the business and ranks <em>winnable</em>{" "}
        keywords — watch the impossible high-difficulty head term sink to the bottom.
      </p>

      {error && <div className="error">⚠ {error}</div>}

      {plan && (
        <div className="result">
          <div className="profile-chips">
            <span className="chip">type: {plan.profile.type}</span>
            <span className="chip">maturity: {plan.profile.maturity}</span>
            <span className="chip">authority: {plan.profile.authority_band}</span>
            {plan.profile.is_geo_relevant && <span className="chip">geo-relevant</span>}
          </div>

          {plan.executive_summary && <div className="summary">{plan.executive_summary}</div>}

          <table>
            <thead>
              <tr>
                <th>Winnable keyword</th>
                <th className="opp">Opportunity</th>
              </tr>
            </thead>
            <tbody>
              {plan.keywords.map((k, i) => (
                <tr key={k.term} className={i === 0 ? "kw-top" : ""}>
                  <td title={k.rationale}>{k.term}</td>
                  <td className="opp">{k.opportunity}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {plan.actions.length > 0 && (
            <table style={{ marginTop: "1.25rem" }}>
              <thead>
                <tr>
                  <th>Prioritised action</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {plan.actions.map((a, i) => (
                  <tr key={i}>
                    <td>{a.description}</td>
                    <td>{a.risk}</td>
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
