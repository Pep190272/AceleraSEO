"use client";

import { useRef, useState } from "react";

import { useT } from "@/lib/i18n";

type Scored = { term: string; opportunity: number; rationale: string };
type Action = { kind: string; target_url: string; risk: string; description: string };
type Plan = {
  profile: { type: string; maturity: string; authority_band: string; is_geo_relevant: boolean };
  executive_summary: string;
  keywords: Scored[];
  actions: Action[];
};

const MATURITY = [
  { key: "strat.mat.new", value: 8 },
  { key: "strat.mat.growing", value: 120 },
  { key: "strat.mat.established", value: 600 },
];

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

function verdict(opportunity: number, max: number, t: (k: string) => string) {
  const ratio = max > 0 ? opportunity / max : 0;
  if (ratio >= 0.6) return { label: t("res.verdict.best"), cls: "v-best" };
  if (ratio >= 0.25) return { label: t("res.verdict.good"), cls: "v-good" };
  if (ratio >= 0.08) return { label: t("res.verdict.hard"), cls: "v-hard" };
  return { label: t("res.verdict.skip"), cls: "v-skip" };
}

export default function StrategyTool() {
  const { t, lang } = useT();
  const [mode, setMode] = useState<"discover" | "paste">("discover");
  const [maturity, setMaturity] = useState(MATURITY[0].value);
  const [isLocal, setIsLocal] = useState(true);
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [kwText, setKwText] = useState(SAMPLE);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  async function run() {
    setLoading(true);
    setError("");
    setPlan(null);
    try {
      const snapshot = {
        ranking_query_count: Number(maturity),
        has_local_signals: isLocal,
      };
      const endpoint = mode === "discover" ? "/api/strategy/discover" : "/api/strategy";
      const payload =
        mode === "discover"
          ? { snapshot, business_description: description, location, language: lang }
          : { snapshot, keywords: parseKeywords(kwText) };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Engine error");
      setPlan(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const max = plan ? Math.max(...plan.keywords.map((k) => k.opportunity), 0) : 0;

  return (
    <div className="panel">
      <p className="lead">{t("strat.lead")}</p>

      <div className="mode-switch">
        <button
          className={mode === "discover" ? "on" : ""}
          onClick={() => setMode("discover")}
          type="button"
        >
          {t("strat.mode.discover")}
        </button>
        <button
          className={mode === "paste" ? "on" : ""}
          onClick={() => setMode("paste")}
          type="button"
        >
          {t("strat.mode.paste")}
        </button>
      </div>

      <div className="row">
        <div>
          <label>{t("strat.q1")}</label>
          <select
            className="select"
            value={maturity}
            onChange={(e) => setMaturity(Number(e.target.value))}
          >
            {MATURITY.map((m) => (
              <option key={m.value} value={m.value}>{t(m.key)}</option>
            ))}
          </select>
        </div>
        <div>
          <label>{t("strat.q2")}</label>
          <select
            className="select"
            value={isLocal ? "yes" : "no"}
            onChange={(e) => setIsLocal(e.target.value === "yes")}
          >
            <option value="yes">{t("strat.local.yes")}</option>
            <option value="no">{t("strat.local.no")}</option>
          </select>
        </div>
      </div>

      {mode === "discover" ? (
        <>
          <div className="field">
            <label>{t("strat.describe.label")}</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder={t("strat.describe.ph")}
            />
          </div>
          <div className="field">
            <label>{t("strat.location.label")}</label>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder={t("strat.location.ph")}
            />
          </div>
        </>
      ) : (
        <div className="field">
          <label>
            {t("strat.paste.label")}{" "}
            <span style={{ color: "var(--muted)", fontWeight: 400 }}>— {t("strat.paste.hint")}</span>
          </label>
          <textarea value={kwText} onChange={(e) => setKwText(e.target.value)} rows={6} />
          <button className="link-btn" onClick={() => setKwText(SAMPLE)} type="button">
            {t("strat.reset")}
          </button>
        </div>
      )}

      <button className="primary" onClick={run} disabled={loading}>
        {loading
          ? t("strat.thinking")
          : mode === "discover"
            ? t("strat.run.discover")
            : t("strat.run.paste")}
      </button>

      {error && <div className="error">⚠ {error}</div>}

      {plan && (
        <div className="result" ref={resultRef}>
          <h2 className="result-title">{t("res.title")}</h2>

          <p className="plain-profile">
            {t("res.profile.a")}{" "}
            <strong>
              {plan.profile.maturity}{" "}
              {plan.profile.is_geo_relevant ? "local " : ""}
              {plan.profile.type}
            </strong>{" "}
            {t("res.profile.b")} <strong>{plan.profile.authority_band}</strong>
            {t("res.profile.c")}
          </p>

          <table>
            <thead>
              <tr>
                <th>{t("res.col.keyword")}</th>
                <th>{t("res.col.verdict")}</th>
                <th className="opp">{t("res.col.score")}</th>
              </tr>
            </thead>
            <tbody>
              {plan.keywords.map((k) => {
                const v = verdict(k.opportunity, max, t);
                return (
                  <tr key={k.term}>
                    <td>{k.term}</td>
                    <td><span className={`verdict ${v.cls}`}>{v.label}</span></td>
                    <td className="opp" title={k.rationale}>{k.opportunity}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="hint">{t("res.verdict.hint")}</p>

          {plan.actions.length > 0 && (
            <>
              <h3 className="result-sub">{t("res.actions.title")}</h3>
              <ol className="actions">
                {plan.actions.map((a, i) => (
                  <li key={i}>
                    {a.description}
                    {a.risk === "high" && <span className="tag-high"> {t("res.actions.fixfirst")}</span>}
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      )}
    </div>
  );
}
