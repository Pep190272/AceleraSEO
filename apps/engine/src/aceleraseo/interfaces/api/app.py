"""FastAPI surface for SENSE: Google OAuth consent + trigger a collection cycle."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ...application.crawl import CrawlSite
from ...application.sense import CollectSignals
from ...domain.models import Severity
from ...infrastructure.config import get_settings
from ...infrastructure.google import oauth
from ...infrastructure.google.ga4_adapter import GA4AnalyticsProvider
from ...infrastructure.google.gsc_adapter import GSCRankingProvider
from ...infrastructure.persistence.db import make_session_factory
from ...infrastructure.persistence.repository import RankingRepository
from ...infrastructure.providers.crawler import HttpxCrawler

app = FastAPI(title="AceleraSEO — Engine", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/settings")
def get_settings_schema() -> dict:
    """Field definitions + current state for the Settings tab. Secrets masked."""
    from ...infrastructure.config import is_demo_mode
    from ...infrastructure.settings_store import describe

    return {"demo_mode": is_demo_mode(), "fields": describe(get_settings())}


class _SettingsIn(BaseModel):
    values: dict[str, str]


@app.post("/settings")
def update_settings(body: _SettingsIn) -> dict:
    """Persist UI-provided config (no .env editing). Blocked in demo mode."""
    from ...infrastructure.config import is_demo_mode, reload_settings
    from ...infrastructure.settings_store import describe, save_overrides

    if is_demo_mode():
        raise HTTPException(
            403,
            "This is a shared demo — settings are read-only. Self-host to configure "
            "your own keys (see the README).",
        )
    save_overrides(body.values)
    reload_settings()
    return {"saved": True, "fields": describe(get_settings())}


@app.post("/settings/verify-llm")
def verify_llm_key() -> dict:
    """Check the currently-saved LLM key against Anthropic (no tokens spent).

    Lets the Settings tab confirm a pasted key is active and valid instead of
    leaving the user to find out only when a later operation fails."""
    from ...infrastructure.llm.factory import verify_llm

    return verify_llm(get_settings())


@app.get("/auth/google/login")
def google_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise HTTPException(500, "Google OAuth client not configured (.env).")
    return RedirectResponse(oauth.authorization_url(settings))


@app.get("/auth/google/callback")
def google_callback(code: str = Query(...)) -> dict:
    settings = get_settings()
    oauth.exchange_code(settings, code)
    return {"status": "authorized", "message": "Token cached. You can now run /sense/run."}


@app.post("/sense/run")
def sense_run(days: int = 90) -> dict:
    settings = get_settings()
    creds = oauth.load_credentials(settings)
    if creds is None:
        raise HTTPException(401, "Not authorized. Visit /auth/google/login first.")
    if not settings.gsc_site_url:
        raise HTTPException(400, "GSC_SITE_URL not set in .env.")

    session_factory = make_session_factory(settings.database_url)
    use_case = CollectSignals(
        rankings=GSCRankingProvider(creds),
        analytics=GA4AnalyticsProvider(creds),
        repository=RankingRepository(session_factory),
    )
    result = use_case.execute(
        site_url=settings.gsc_site_url,
        property_id=settings.ga4_property_id,
        days=days,
    )
    return {
        "rankings_fetched": result.rankings_fetched,
        "rankings_new": result.rankings_new,
        "pages_with_conversions": result.pages_with_conversions,
    }


@app.post("/audit/run")
def audit_run(start_url: str, max_pages: int = 200, max_depth: int = 5,
              render: bool = False) -> dict:
    """Crawl a site and return a severity-tagged technical SEO audit.

    render=True drives a headless browser (Playwright) for JS-rendered / SPA
    sites where the raw HTML has no links. Requires the `render` extra.
    """
    if render:
        from ...infrastructure.providers.rendering_crawler import RenderingCrawler
        crawler = RenderingCrawler()
    else:
        crawler = HttpxCrawler()
    try:
        report = CrawlSite(crawler).execute(start_url, max_pages=max_pages, max_depth=max_depth)
    finally:
        crawler.close()
    return {
        "pages_crawled": len(report.pages),
        "critical": report.count(Severity.CRITICAL),
        "warning": report.count(Severity.WARNING),
        "notice": report.count(Severity.NOTICE),
        "issues": [
            {"code": i.code, "severity": i.severity.value, "url": i.url, "message": i.message}
            for i in report.issues
        ],
    }


class _KeywordIn(BaseModel):
    term: str
    search_volume: int = 0
    difficulty: float = 0.0
    intent: str = "informational"


class _StrategyIn(BaseModel):
    snapshot: dict = {}
    keywords: list[_KeywordIn] = []


class _DiscoverIn(BaseModel):
    snapshot: dict = {}
    business_description: str = ""
    location: str = ""
    language: str = "en"
    max_keywords: int = 20


@app.post("/strategy/discover")
def strategy_discover(body: _DiscoverIn) -> dict:
    """Describe your niche -> the LLM finds keywords (DataForSEO enriches), then
    the engine ranks the winnable ones. Needs an LLM key, so it is unavailable
    in the keyless demo (returns 422 with a clear message)."""
    from ...application.decide import BuildStrategy
    from ...domain.models import SiteSnapshot
    from ...infrastructure.llm.factory import make_discoverer, make_llm, make_market

    if not body.business_description.strip():
        raise HTTPException(422, "Describe your business/niche first.")

    settings = get_settings()
    discoverer = make_discoverer(settings)
    if discoverer is None:
        raise HTTPException(
            422,
            "Keyword discovery needs an LLM API key. This shared demo runs keyless — "
            "paste your own keywords below, or self-host and add your key in Settings.",
        )

    from ...application.discover import DiscoverKeywords
    candidates = DiscoverKeywords(discoverer, make_market(settings)).execute(
        body.business_description, body.location, body.language, body.max_keywords
    )
    snapshot = SiteSnapshot(**body.snapshot)
    plan = BuildStrategy(make_llm(settings)).execute(snapshot, candidates)
    return _serialise_plan(plan)


@app.post("/strategy/preview")
def strategy_preview(body: _StrategyIn) -> dict:
    """DECIDE: classify + score keywords + derive actions + LLM summary.

    Accepts keyword metrics directly so it works without a market API key. Uses
    the configured LLM, or NullLLM if none is set (plan is still produced).
    """
    from ...application.decide import BuildStrategy
    from ...domain.models import Keyword, SiteSnapshot
    from ...infrastructure.llm.factory import make_llm

    snapshot = SiteSnapshot(**body.snapshot)
    candidates = [Keyword(term=k.term, search_volume=k.search_volume,
                          difficulty=k.difficulty, intent=k.intent) for k in body.keywords]

    plan = BuildStrategy(make_llm(get_settings())).execute(snapshot, candidates)
    return _serialise_plan(plan)


def _serialise_plan(plan) -> dict:
    return {
        "profile": {
            "type": plan.profile.type.value,
            "maturity": plan.profile.maturity.value,
            "authority_band": plan.profile.authority_band.value,
            "is_geo_relevant": plan.profile.is_geo_relevant,
        },
        "executive_summary": plan.executive_summary,
        "keywords": [
            {"term": s.keyword.term, "opportunity": s.opportunity, "rationale": s.rationale}
            for s in plan.keywords
        ],
        "actions": [
            {"kind": a.kind, "target_url": a.target_url, "risk": a.risk,
             "description": a.description, "rationale": a.rationale}
            for a in plan.actions
        ],
    }


# ── CMS on-page management endpoints ─────────────────────────

@app.get("/cms/audit")
def cms_audit() -> dict:
    """Return the SEO health audit for the managed Noor site.

    Returns 503 with a clear message when Noor credentials are not configured,
    mirroring the /competitors/analyze pattern so the UI can surface a helpful
    message rather than a raw 500.
    """
    from ...application.cms import GetSiteAudit
    from ...infrastructure.llm.factory import make_cms

    settings = get_settings()
    cms = make_cms(settings)
    if cms is None:
        raise HTTPException(
            503,
            "Noor CMS integration requires NOOR_BASE_URL and NOOR_API_KEY. "
            "Configure them in the Settings tab → Noor CMS.",
        )

    audit = GetSiteAudit(cms).execute()
    return {
        "keywords": {
            "total": audit.keywords.total,
            "active": audit.keywords.active,
            "urls_configured": list(audit.keywords.urls_configured),
            "urls_missing_meta": list(audit.keywords.urls_missing_meta),
        },
        "textos": {
            "total": audit.textos.total,
            "active": audit.textos.active,
            "urls_configured": list(audit.textos.urls_configured),
        },
        "images": {
            "total": audit.images.total,
            "portfolio_images": audit.images.portfolio_images,
            "portfolio_missing_alt": audit.images.portfolio_missing_alt,
            "contenido_multimedia": audit.images.contenido_multimedia,
        },
        "blog": {
            "total_posts": audit.blog.total_posts,
            "posts_without_cover": audit.blog.posts_without_cover,
            "posts_without_meta": audit.blog.posts_without_meta,
        },
        "portfolio": {
            "published": audit.portfolio.published,
        },
    }


@app.get("/cms/pages")
def cms_list_pages() -> dict:
    """Return all SEO-managed pages for the Noor site."""
    from ...application.cms import ListSeoPages
    from ...infrastructure.llm.factory import make_cms

    settings = get_settings()
    cms = make_cms(settings)
    if cms is None:
        raise HTTPException(
            503,
            "Noor CMS integration requires NOOR_BASE_URL and NOOR_API_KEY. "
            "Configure them in the Settings tab → Noor CMS.",
        )

    pages = ListSeoPages(cms).execute()
    return {
        "pages": [
            {
                "url": p.url,
                "h1": p.h1,
                "h2": p.h2,
                "hero_title": p.hero_title,
                "meta_title": p.meta_title,
                "meta_description": p.meta_description,
            }
            for p in pages
        ]
    }


class _SeoPageIn(BaseModel):
    url: str
    h1: str
    h2: str | None = None
    hero_title: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None


@app.put("/cms/pages")
def cms_update_page(body: _SeoPageIn) -> dict:
    """Create or fully-replace a page's SEO metadata in the Noor site.

    Requires url (url_path) and h1 (keyword_h1). All other fields are optional
    but MUST be included if they were previously set — Noor performs a full
    replace, so omitting an optional field will clear it in the DB.
    The use-case validates h1 (>=3 non-whitespace chars, no angle brackets, <=60)
    and returns a clear error rather than a raw 422.
    """
    from ...application.cms import UpdateSeoPage
    from ...domain.models import SeoPage
    from ...infrastructure.llm.factory import make_cms

    settings = get_settings()
    cms = make_cms(settings)
    if cms is None:
        raise HTTPException(
            503,
            "Noor CMS integration requires NOOR_BASE_URL and NOOR_API_KEY. "
            "Configure them in the Settings tab → Noor CMS.",
        )

    page = SeoPage(
        url=body.url,
        h1=body.h1,
        h2=body.h2,
        hero_title=body.hero_title,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
    )
    try:
        result = UpdateSeoPage(cms).execute(page)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return result


@app.post("/settings/verify-cms")
def verify_cms_key() -> dict:
    """Probe the Noor CMS API key without performing a write.

    Returns {"ok": bool, "detail": str}. Mirrors /settings/verify-llm so the
    Settings tab can use the same connection-test button pattern.
    """
    from ...infrastructure.llm.factory import verify_cms

    return verify_cms(get_settings())


class _CompetitorIn(BaseModel):
    domain: str
    location: str = ""
    language: str = "es"


@app.post("/competitors/analyze")
def competitors_analyze(body: _CompetitorIn) -> dict:
    """Find top organic competitors for a domain and their ranked keywords.

    Requires DataForSEO credentials. Returns a 503 with a clear message if
    they are absent so the UI can surface a helpful error rather than a raw 500.
    """
    from ...application.competitors import (
        MAX_COMPETITORS,
        MAX_KEYWORDS_PER_COMPETITOR,
        AnalyzeCompetitors,
    )
    from ...infrastructure.llm.factory import make_competitor

    if not body.domain.strip():
        raise HTTPException(422, "A target domain is required.")

    settings = get_settings()
    provider = make_competitor(settings)
    if provider is None:
        raise HTTPException(
            503,
            "Competitor analysis requires DataForSEO credentials (DATAFORSEO_LOGIN + "
            "DATAFORSEO_PASSWORD). Configure them in the Settings tab.",
        )

    competitors = AnalyzeCompetitors(provider).execute(
        target=body.domain.strip(),
        location=body.location,
        language=body.language,
        max_competitors=MAX_COMPETITORS,
        max_keywords_per_competitor=MAX_KEYWORDS_PER_COMPETITOR,
    )
    return {
        "domain": body.domain.strip(),
        "competitors": [
            {
                "domain": c.domain,
                "common_keywords": c.common_keywords,
                "avg_position": c.avg_position,
                "organic_traffic": c.organic_traffic,
                "ranked_keywords": [
                    {"term": kw.term, "position": kw.position, "search_volume": kw.search_volume}
                    for kw in c.ranked_keywords
                ],
            }
            for c in competitors
        ],
    }


class _IndexNowIn(BaseModel):
    urls: list[str]


@app.post("/act/indexnow")
def act_indexnow(body: _IndexNowIn) -> dict:
    """Submit URLs for instant indexing on Bing/Yandex/etc (NOT Google)."""
    from ...infrastructure.providers.indexnow import IndexNowIndexer

    settings = get_settings()
    if not settings.indexnow_key:
        raise HTTPException(400, "INDEXNOW_KEY not set in .env.")
    indexer = IndexNowIndexer(settings.indexnow_key, settings.indexnow_key_location)
    ok = indexer.submit(body.urls)
    return {"submitted": ok, "count": len(body.urls),
            "note": "Google does not support IndexNow; use sitemap + /act/index-status."}


@app.get("/act/index-status")
def act_index_status(url: str = Query(...)) -> dict:
    """Check whether Google has indexed a URL (read-only monitor — never forces)."""
    from ...infrastructure.google.url_inspection_adapter import URLInspectionReader

    settings = get_settings()
    creds = oauth.load_credentials(settings)
    if creds is None:
        raise HTTPException(401, "Not authorized. Visit /auth/google/login first.")
    reader = URLInspectionReader(creds, settings.gsc_site_url)
    status = reader.inspect(url)
    return {"url": status.url, "indexed": status.indexed, "via": status.checked_via}


@app.get("/act/proposals")
def list_proposals() -> dict:
    """Pending actions awaiting human approval (AUTONOMY_MODE=none default)."""
    from ...infrastructure.persistence.proposals import ProposalRepository

    repo = ProposalRepository(make_session_factory(get_settings().database_url))
    return {"pending": repo.pending()}


@app.post("/act/proposals/{proposal_id}/{status}")
def update_proposal(proposal_id: int, status: str) -> dict:
    """Approve or reject a proposed action."""
    from ...infrastructure.persistence.proposals import ProposalRepository

    if status not in ("approved", "rejected"):
        raise HTTPException(400, "status must be 'approved' or 'rejected'.")
    repo = ProposalRepository(make_session_factory(get_settings().database_url))
    if not repo.set_status(proposal_id, status):
        raise HTTPException(404, "Proposal not found.")
    return {"id": proposal_id, "status": status}


@app.get("/learn/outcome")
def learn_outcome(action_date: str, window_days: int = 28) -> dict:
    """Close the loop: did rankings move after the action on action_date?

    Compares the persisted window before vs after the date (ISO yyyy-mm-dd).
    """
    from datetime import date as _date

    from ...application.learn import MeasureOutcomes, summarize
    from ...infrastructure.persistence.repository import RankingRepository

    settings = get_settings()
    if not settings.gsc_site_url:
        raise HTTPException(400, "GSC_SITE_URL not set in .env.")
    repo = RankingRepository(make_session_factory(settings.database_url))
    report = MeasureOutcomes(repo).execute(
        settings.gsc_site_url, _date.fromisoformat(action_date), window_days
    )
    return {
        "summary": summarize(report),
        "deltas": [
            {"query": d.query, "trend": d.trend.value,
             "position_before": d.position_before, "position_after": d.position_after,
             "position_change": d.position_change,
             "clicks_before": d.clicks_before, "clicks_after": d.clicks_after}
            for d in report.deltas
        ],
    }
