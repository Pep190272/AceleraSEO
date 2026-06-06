"use client";

import type { RefObject } from "react";

import { useT } from "@/lib/i18n";
import type { Plan } from "@/lib/types/api";

// ---------------------------------------------------------------------------
// Local constants — kept here so the view is self-contained for rendering
// ---------------------------------------------------------------------------

export const MATURITY = [
  { key: "strat.mat.new", value: 8 },
  { key: "strat.mat.growing", value: 120 },
  { key: "strat.mat.established", value: 600 },
];

export const SAMPLE = `fontanero, 40000, 88, commercial
fontanero urgente gracia barcelona, 210, 14, transactional
reparar fuga agua barcelona, 480, 22, transactional
precio reparacion caldera, 2900, 61, commercial`;

// ---------------------------------------------------------------------------
// Pure helpers — no side effects, no fetch
// ---------------------------------------------------------------------------

export function parseKeywords(raw: string) {
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

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type StrategyViewProps = {
  mode: "discover" | "paste";
  maturity: number;
  isLocal: boolean;
  description: string;
  location: string;
  kwText: string;
  plan: Plan | null;
  error: string;
  loading: boolean;
  resultRef: RefObject<HTMLDivElement | null>;
  onModeChange: (mode: "discover" | "paste") => void;
  onMaturityChange: (value: number) => void;
  onIsLocalChange: (value: boolean) => void;
  onDescriptionChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onKwTextChange: (value: string) => void;
  onResetSample: () => void;
  onRun: () => void;
};

// ---------------------------------------------------------------------------
// Presentational component — no data fetching, no business logic
// ---------------------------------------------------------------------------

export default function StrategyView({
  mode,
  maturity,
  isLocal,
  description,
  location,
  kwText,
  plan,
  error,
  loading,
  resultRef,
  onModeChange,
  onMaturityChange,
  onIsLocalChange,
  onDescriptionChange,
  onLocationChange,
  onKwTextChange,
  onResetSample,
  onRun,
}: StrategyViewProps) {
  const { t } = useT();

  const max = plan ? Math.max(...plan.keywords.map((k) => k.opportunity), 0) : 0;

  return (
    <div className="panel">
      <p className="lead">{t("strat.lead")}</p>

      <div className="mode-switch">
        <button
          className={mode === "discover" ? "on" : ""}
          onClick={() => onModeChange("discover")}
          type="button"
        >
          {t("strat.mode.discover")}
        </button>
        <button
          className={mode === "paste" ? "on" : ""}
          onClick={() => onModeChange("paste")}
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
            onChange={(e) => onMaturityChange(Number(e.target.value))}
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
            onChange={(e) => onIsLocalChange(e.target.value === "yes")}
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
              onChange={(e) => onDescriptionChange(e.target.value)}
              rows={4}
              placeholder={t("strat.describe.ph")}
            />
          </div>
          <div className="field">
            <label>{t("strat.location.label")}</label>
            <input
              value={location}
              onChange={(e) => onLocationChange(e.target.value)}
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
          <textarea value={kwText} onChange={(e) => onKwTextChange(e.target.value)} rows={6} />
          <button className="link-btn" onClick={onResetSample} type="button">
            {t("strat.reset")}
          </button>
        </div>
      )}

      <button className="primary" onClick={onRun} disabled={loading}>
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
