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

// ── SiteTool ──────────────────────────────────────────────────

export type KeywordStats = {
  total: number;
  active: number;
  urls_configured: string[];
  urls_missing_meta: string[];
};

export type TextStats = {
  total: number;
  active: number;
  urls_configured: string[];
};

export type ImageStats = {
  total: number;
  portfolio_images: number;
  portfolio_missing_alt: number;
  contenido_multimedia: number;
};

export type BlogStats = {
  total_posts: number;
  posts_without_cover: number;
  posts_without_meta: number;
};

export type PortfolioStats = {
  published: number;
};

export type SeoAudit = {
  keywords: KeywordStats;
  textos: TextStats;
  images: ImageStats;
  blog: BlogStats;
  portfolio: PortfolioStats;
};

export type SeoPage = {
  url: string;
  h1: string;
  h2: string | null;
  hero_title: string | null;
  meta_title: string | null;
  meta_description: string | null;
};
