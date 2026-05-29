"""FastAPI surface for SENSE: Google OAuth consent + trigger a collection cycle."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

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
