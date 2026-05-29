"""Domain models — pure data, no I/O, no framework dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class BusinessType(str, Enum):
    LOCAL = "local"
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    BLOG = "blog"
    CORPORATE = "corporate"


class Maturity(str, Enum):
    NEW = "new"
    GROWING = "growing"
    ESTABLISHED = "established"


class AuthorityBand(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


@dataclass(frozen=True)
class BusinessProfile:
    """Output of the classification stage — drives strategy selection."""
    type: BusinessType
    maturity: Maturity
    authority_band: AuthorityBand
    is_geo_relevant: bool


@dataclass(frozen=True)
class RankingSignal:
    """A single GSC observation for a query/page on a given day."""
    query: str
    page: str
    position: float
    clicks: int
    impressions: int
    ctr: float
    observed_on: date


@dataclass(frozen=True)
class Keyword:
    term: str
    search_volume: int
    difficulty: float          # 0..100
    intent: str                # informational | transactional | navigational | commercial
    business_value: float = 1.0


@dataclass(frozen=True)
class ScoredKeyword:
    keyword: Keyword
    opportunity: float
    rationale: str             # human-readable explanation (mandatory — trust)


@dataclass(frozen=True)
class Action:
    kind: str                  # indexnow_ping | content_brief | onpage_fix | sitemap_update
    target_url: str
    description: str
    risk: str                  # low | medium | high
    rationale: str


@dataclass
class ActionPlan:
    profile: BusinessProfile
    keywords: list[ScoredKeyword] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    executive_summary: str = ""   # LLM-written narrative; empty if no LLM configured


@dataclass(frozen=True)
class SiteSnapshot:
    """Aggregated signals the classifier needs — derived from SENSE + M2 crawl.

    Pure input: the use case builds this from real data, the classifier reads it.
    Keeps classification deterministic and testable with no I/O.
    """
    ranking_query_count: int = 0      # distinct queries the site ranks for (GSC)
    total_clicks: int = 0             # search clicks in the window (GSC)
    avg_position: float = 0.0         # mean position across ranking queries (GSC)
    total_pages: int = 0             # pages found by the crawler (M2)
    ecommerce_pages: int = 0          # pages with product/cart signals (M2)
    blog_pages: int = 0              # pages under /blog or with article schema (M2)
    has_local_signals: bool = False   # NAP / city terms / LocalBusiness schema


# ─────────────────────────────────────────────────────────────
# M2 — Technical crawler / audit
# ─────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"   # blocks ranking/indexing — fix now
    WARNING = "warning"     # hurts SEO — fix soon
    NOTICE = "notice"       # improvement opportunity


@dataclass(frozen=True)
class CrawledPage:
    """A fetched + parsed page. Pure data — the adapter builds it, audit reads it."""
    url: str
    status_code: int
    title: str | None = None
    meta_description: str | None = None
    h1s: tuple[str, ...] = ()
    canonical: str | None = None
    internal_links: tuple[str, ...] = ()
    external_links: tuple[str, ...] = ()
    word_count: int = 0
    has_schema: bool = False
    robots_noindex: bool = False


@dataclass(frozen=True)
class AuditIssue:
    """One finding on one URL — severity-tagged with a cited reason."""
    code: str
    severity: Severity
    url: str
    message: str


@dataclass(frozen=True)
class IndexStatus:
    """Result of monitoring a URL's presence in Google (read-only)."""
    url: str
    indexed: bool
    checked_via: str = "url_inspection"


# ─────────────────────────────────────────────────────────────
# M5 — LEARN (close the loop)
# ─────────────────────────────────────────────────────────────

class Trend(str, Enum):
    IMPROVED = "improved"     # position got closer to 1 (lower number)
    DECLINED = "declined"
    STABLE = "stable"
    NEW = "new"               # query appeared only in the 'after' window
    LOST = "lost"             # query present 'before' but gone 'after'


@dataclass(frozen=True)
class OutcomeDelta:
    """How one query moved between two measurement windows."""
    query: str
    position_before: float | None
    position_after: float | None
    clicks_before: int
    clicks_after: int
    trend: Trend

    @property
    def position_change(self) -> float | None:
        if self.position_before is None or self.position_after is None:
            return None
        # Negative = improved (moved up the SERP).
        return round(self.position_after - self.position_before, 2)


@dataclass
class OutcomeReport:
    """The LEARN result — what changed, fed back into DECIDE next cycle."""
    deltas: list[OutcomeDelta] = field(default_factory=list)

    def by_trend(self, trend: Trend) -> list[OutcomeDelta]:
        return [d for d in self.deltas if d.trend is trend]

    @property
    def net_clicks_change(self) -> int:
        return sum(d.clicks_after - d.clicks_before for d in self.deltas)


@dataclass
class CrawlReport:
    pages: list[CrawledPage] = field(default_factory=list)
    issues: list[AuditIssue] = field(default_factory=list)

    def count(self, severity: Severity) -> int:
        return sum(1 for i in self.issues if i.severity is severity)
