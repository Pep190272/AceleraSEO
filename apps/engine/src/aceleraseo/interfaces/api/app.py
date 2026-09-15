"""FastAPI surface for SENSE: Google OAuth consent + trigger a collection cycle."""
from __future__ import annotations

import logging
import socket
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import GoogleAuthError, TransportError
from googleapiclient.errors import HttpError
from httplib2 import HttpLib2Error
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
from ...infrastructure.providers.url_safety import UnsafeURLError, ensure_public_url
from .guards import require_token, require_write_access, warn_if_token_missing

logger = logging.getLogger(__name__)

app = FastAPI(title="AceleraSEO — Engine", version="0.1.0")
warn_if_token_missing()

# Endpoints that change state (settings, the database, a managed site, or an
# external index) must declare this. See guards.py.
_WRITE = [Depends(require_write_access)]
# Endpoints that spend a provider's quota or fetch URLs: token only, so the demo works.
_COSTLY = [Depends(require_token)]


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


@app.post("/settings", dependencies=_WRITE)
def update_settings(body: _SettingsIn) -> dict:
    """Persist UI-provided config (no .env editing). Blocked in demo mode (_WRITE)."""
    from ...infrastructure.config import reload_settings
    from ...infrastructure.settings_store import describe, save_overrides

    save_overrides(body.values)
    reload_settings()
    return {"saved": True, "fields": describe(get_settings())}


@app.post("/settings/verify-llm", dependencies=_COSTLY)
def verify_llm_key() -> dict:
    """Check the currently-saved LLM key against Anthropic (no tokens spent).

    Lets the Settings tab confirm a pasted key is active and valid instead of
    leaving the user to find out only when a later operation fails."""
    from ...infrastructure.llm.factory import verify_llm

    return verify_llm(get_settings())


_DEMO_GOOGLE_MESSAGE = (
    "This is a shared demo — connecting a Google account is disabled, because the "
    "token would be shared with every visitor. Self-host to connect your own account."
)

_GOOGLE_UNREACHABLE_MESSAGE = (
    "Could not reach Google — check the engine's internet connection and try again."
)
_GOOGLE_TIMEOUT_MESSAGE = "Google did not answer in time. Try again in a moment."


@app.get("/auth/google/status")
def google_status() -> dict:
    """Whether Google OAuth is configured and a usable token is cached.

    Booleans only — never a token, client id or secret."""
    settings = get_settings()
    return {
        "configured": oauth.is_configured(settings),
        "connected": oauth.is_connected(settings),
    }


@app.get("/auth/google/login")
def google_login() -> RedirectResponse:
    """Start Google consent. Blocked in demo mode, like writing settings."""
    from ...infrastructure.config import is_demo_mode

    if is_demo_mode():
        raise HTTPException(403, _DEMO_GOOGLE_MESSAGE)
    settings = get_settings()
    if not oauth.is_configured(settings):
        raise HTTPException(
            400,
            "Google OAuth is not configured. Add the OAuth client ID and secret in the "
            "Settings tab → Google.",
        )
    return RedirectResponse(oauth.authorization_url(settings))


def _back_to_settings(outcome: str, reason: str | None = None) -> RedirectResponse:
    """Send the browser back to the dashboard Settings tab with the consent outcome."""
    params = {"tab": "settings", "google": outcome}
    if reason:
        params["reason"] = reason
    base = get_settings().dashboard_url.rstrip("/")
    return RedirectResponse(f"{base}/?{urlencode(params)}", status_code=303)


@app.get("/auth/google/callback")
def google_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
) -> RedirectResponse:
    """Google redirects here after consent. Always answers with a redirect to the
    dashboard, so the user never lands on a bare JSON page."""
    from ...infrastructure.config import is_demo_mode

    if is_demo_mode():
        return _back_to_settings("error", "demo")
    if error:
        # The user cancelled (access_denied) or Google refused the request.
        if state:
            oauth.discard_state(state)
        return _back_to_settings("error", "denied" if error == "access_denied" else "failed")
    if not code or not state:
        return _back_to_settings("error", "invalid_request")

    try:
        oauth.exchange_code(get_settings(), code, state)
    except oauth.InvalidStateError:
        return _back_to_settings("error", "state")
    except Exception:
        # Token endpoint rejection, network failure or scope mismatch. Logged with
        # the traceback; the user gets a readable message and can retry.
        logger.exception("Google OAuth code exchange failed.")
        return _back_to_settings("error", "exchange")
    return _back_to_settings("connected")


@app.post("/sense/run", dependencies=_WRITE)
def sense_run(days: int = Query(90, ge=1, le=480)) -> dict:
    """Run a SENSE collection cycle against Search Console (+ GA4 if configured).

    Failure modes are mapped to a message the caller can show as-is, never a
    raw 500: no connection (401), a broken/corrupt saved token (401, same
    remedy — reconnect), a missing site URL (400), and Google itself
    rejecting or rate-limiting the request once collection is under way
    (400/401/429/502), or Google being unreachable or too slow (502/504)."""
    settings = get_settings()
    try:
        creds = oauth.load_credentials(settings)
    except (OSError, ValueError) as exc:
        # Corrupt or unreadable token file — same remedy as never having
        # connected, so this is a 401 rather than a raw 500. Mirrors
        # oauth.is_connected()'s handling of the same failure.
        logger.warning("Google token file is unreadable or corrupt (%s).", type(exc).__name__)
        raise HTTPException(
            401,
            "Google connection is broken (the saved token could not be read). "
            "Reconnect from Settings.",
        ) from exc
    except TransportError as exc:
        # The token expired and refreshing it could not reach Google. The account
        # is fine — the engine's network is not — so do not tell the user to reconnect.
        logger.warning("Google token refresh could not reach Google (%s).", type(exc).__name__)
        raise HTTPException(502, _GOOGLE_UNREACHABLE_MESSAGE) from exc
    except GoogleAuthError as exc:
        logger.warning("Google token refresh failed (%s).", type(exc).__name__)
        raise HTTPException(
            401,
            "Google connection expired or was revoked. Reconnect from Settings.",
        ) from exc
    if creds is None:
        raise HTTPException(401, "Not authorized. Visit /auth/google/login first.")
    if not settings.gsc_site_url:
        raise HTTPException(
            400,
            "GSC_SITE_URL is not set. Add the Search Console site URL in the "
            "Settings tab → Google.",
        )

    session_factory = make_session_factory(settings.database_url)
    use_case = CollectSignals(
        rankings=GSCRankingProvider(creds),
        analytics=GA4AnalyticsProvider(creds),
        repository=RankingRepository(session_factory),
    )
    try:
        result = use_case.execute(
            site_url=settings.gsc_site_url,
            property_id=settings.ga4_property_id,
            days=days,
        )
    except (HttpError, GoogleAPICallError) as exc:
        # Search Console (HttpError, googleapiclient) or GA4 (GoogleAPICallError,
        # the gRPC client) rejected or throttled the call once collection was
        # already under way — bad scope, revoked access, quota. Never let this
        # surface as a raw 500; map it to a readable, actionable status.
        if isinstance(exc, HttpError):
            status = exc.resp.status if exc.resp is not None else 502
        else:
            # exc.code is an HTTPStatus enum member (compares equal to its int
            # value, but int() keeps the log line readable as a plain number).
            status = int(exc.code) if exc.code is not None else 502
        logger.warning("Google API call failed during SENSE collection (%s).", status)
        if status in (401, 403):
            raise HTTPException(
                401,
                "Google rejected the request — the connected account may not have "
                "access to this Search Console/GA4 property. Reconnect from Settings.",
            ) from exc
        if status in (400, 404):
            # Google does not recognise the site or property — a configuration
            # problem the user can fix, not an outage.
            raise HTTPException(
                400,
                "Google did not accept the Search Console site URL or GA4 property ID. "
                "Check both in the Settings tab → Google.",
            ) from exc
        if status == 504:
            raise HTTPException(504, _GOOGLE_TIMEOUT_MESSAGE) from exc
        if status == 429:
            raise HTTPException(
                429, "Google's API rate limit was hit. Wait a moment and try again.",
            ) from exc
        raise HTTPException(
            502, "Google's API is unavailable right now. Try again shortly.",
        ) from exc
    except (TimeoutError, RetryError) as exc:
        # A socket timeout (Search Console) or GA4's retry budget running out:
        # Google did not answer in time. Nothing was rejected; retrying may work.
        logger.warning("Google did not answer in time during SENSE collection (%s).",
                       type(exc).__name__)
        raise HTTPException(504, _GOOGLE_TIMEOUT_MESSAGE) from exc
    except (ConnectionError, socket.gaierror, HttpLib2Error, TransportError) as exc:
        # DNS failure, refused/reset connection, or a token refresh that could not
        # reach Google: the engine has no route to Google, not a Google-side error.
        logger.warning("Could not reach Google during SENSE collection (%s).",
                       type(exc).__name__)
        raise HTTPException(502, _GOOGLE_UNREACHABLE_MESSAGE) from exc
    return {
        "rankings_fetched": result.rankings_fetched,
        "rankings_new": result.rankings_new,
        "pages_with_conversions": result.pages_with_conversions,
        # False means conversions were skipped, not that there were zero —
        # CollectSignals.execute() only calls GA4 when a property id is set.
        "ga4_configured": bool(settings.ga4_property_id),
    }


@app.post("/audit/run", dependencies=_COSTLY)
def audit_run(start_url: str, max_pages: int = 200, max_depth: int = 5,
              render: bool = False) -> dict:
    """Crawl a site and return a severity-tagged technical SEO audit.

    render=True drives a headless browser (Playwright) for JS-rendered / SPA
    sites where the raw HTML has no links. Requires the `render` extra.

    The start URL must resolve to public addresses only. The httpx crawler
    re-checks every request, redirects included. The rendering crawler aborts
    private browser requests and discards pages reached through a private redirect,
    but the redirected request still happens and WebSockets are not checked, so
    rendering is off in the demo.
    """
    from ...infrastructure.config import is_demo_mode

    if render and is_demo_mode():
        raise HTTPException(403, "JS rendering is disabled in the shared demo.")
    try:
        ensure_public_url(start_url)
    except UnsafeURLError as exc:
        raise HTTPException(400, str(exc)) from exc
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


@app.post("/strategy/discover", dependencies=_COSTLY)
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


@app.post("/strategy/preview", dependencies=_COSTLY)
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


@app.put("/cms/pages", dependencies=_WRITE)
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


@app.post("/settings/verify-cms", dependencies=_COSTLY)
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


@app.post("/competitors/analyze", dependencies=_COSTLY)
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


@app.post("/act/indexnow", dependencies=_WRITE)
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


@app.post("/act/proposals/{proposal_id}/{status}", dependencies=_WRITE)
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
