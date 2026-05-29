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


@dataclass
class CrawlReport:
    pages: list[CrawledPage] = field(default_factory=list)
    issues: list[AuditIssue] = field(default_factory=list)

    def count(self, severity: Severity) -> int:
        return sum(1 for i in self.issues if i.severity is severity)
