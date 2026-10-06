// Shared API response types for Tool components.
// These are pure data shapes — no behavior, no imports.

// ── StrategyTool ──────────────────────────────────────────────

export type Scored = {
  term: string;
  opportunity: number;
  rationale: string;
};

export type Action = {
  kind: string;
  target_url: string;
  risk: string;
  description: string;
};

export type Plan = {
  profile: {
    type: string;
    maturity: string;
    authority_band: string;
    is_geo_relevant: boolean;
  };
  executive_summary: string;
  keywords: Scored[];
  actions: Action[];
};

// ── AuditTool ─────────────────────────────────────────────────

export type Issue = {
  code: string;
  severity: string;
  url: string;
  message: string;
};

export type Report = {
  pages_crawled: number;
  critical: number;
  warning: number;
  notice: number;
  issues: Issue[];
};

// ── CompetitorTool ────────────────────────────────────────────

export type RankedKeyword = {
  term: string;
  position: number;
  search_volume: number;
};

export type Competitor = {
  domain: string;
  common_keywords: number;
  avg_position: number | null;
  organic_traffic: number;
  ranked_keywords: RankedKeyword[];
};

export type CompetitorResult = {
  domain: string;
  competitors: Competitor[];
};

// ── Google connection (SettingsTool + SenseRunPanel) ──────────

export type GoogleStatus = { configured: boolean; connected: boolean };

// ── SenseRunPanel ────────────────────────────────────────────

export type SenseResult = {
  rankings_fetched: number;
  rankings_new: number;
  pages_with_conversions: number;
  ga4_configured: boolean;
  /** Rows GA4 returned. 0 while configured means the property received no data. */
  ga4_rows: number;
  /** Where conversions came from; "none" means they were skipped. */
  analytics_source: "none" | "ga4" | "wordpress";
  /** Rows the active source returned, whichever it is. */
  conversion_rows: number;
};

// ── RankingsTool (GET /sense/rankings) ───────────────────────

export type RankingRow = {
  query: string;
  clicks: number;
  impressions: number;
  position: number;
  previous_position: number | null;
  // Impressions in the previous window; 0 when the query was not there.
  previous_impressions: number;
  // current − previous; positive means the query slipped. null = not in the
  // previous window, or below min_impressions there (too little data to compare).
  position_delta: number | null;
};

export type RankingsReport = {
  site_url: string;
  window: { start: string; end: string; days: number };
  min_impressions: number;
  first_observed_on: string | null;
  last_observed_on: string | null;
  rows: RankingRow[];
};
