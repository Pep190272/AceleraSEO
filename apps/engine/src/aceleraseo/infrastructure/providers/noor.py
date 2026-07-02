"""Noor CMS adapter — implements domain.ports.CMSPort.

Talks to the Noor REST API (https://construccionesnoor.cloud) via an X-API-Key
header. All domain model mapping is in pure parser functions so they are
unit-testable without network or credentials.

Noor API quirks honoured here:
  - PUT /api/seo/keywords is a FULL REPLACE (not PATCH) — all fields must be sent.
  - url_path is normalised server-side; we canonicalise before sending to avoid
    duplicate-key 422s.
  - Auth errors: 401 = missing key header, 403 = wrong key, 503 = server unconfigured.
"""
from __future__ import annotations

import json as _json
import logging

import httpx

from ...domain.models import (
    BlogStats,
    ImageStats,
    KeywordStats,
    PortfolioStats,
    SeoAudit,
    SeoPage,
    TextStats,
)

logger = logging.getLogger(__name__)


# ── private helpers ───────────────────────────────────────────

def _safe_int(value: object, default: int = 0) -> int:
    """Convert *value* to int without raising on None, '' or non-numeric strings."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_str(value: object, default: str = "") -> str:
    """Return *value* as str or *default* when None / empty."""
    if value is None:
        return default
    return str(value)


def _canonicalize_url_path(raw: str) -> str:
    """Normalize a url_path the same way Noor's server does.

    Rules: lowercase, leading '/', no trailing slash (except root '/').
    Avoids duplicate-key 422 errors from differently-cased or trailing-slash variants.
    """
    path = raw.strip().lower()
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    return path


class NoorCMSError(RuntimeError):
    """Raised when the Noor API returns an expected error (auth, validation, etc.)."""


# ── parsers (pure functions, testable without network) ────────

def parse_audit_response(data: dict) -> SeoAudit:
    """Map the /api/seo/audit JSON to domain.SeoAudit.

    Defensive: any missing or null field falls back to a safe zero value.
    """
    kw = data.get("keywords") or {}
    tx = data.get("textos") or {}
    img = data.get("images") or {}
    bl = data.get("blog") or {}
    pf = data.get("portfolio") or {}

    return SeoAudit(
        keywords=KeywordStats(
            total=_safe_int(kw.get("total")),
            active=_safe_int(kw.get("active")),
            urls_configured=tuple(kw.get("urls_configured") or []),
            urls_missing_meta=tuple(kw.get("urls_missing_meta") or []),
        ),
        textos=TextStats(
            total=_safe_int(tx.get("total")),
            active=_safe_int(tx.get("active")),
            urls_configured=tuple(tx.get("urls_configured") or []),
        ),
        images=ImageStats(
            total=_safe_int(img.get("total")),
            portfolio_images=_safe_int(img.get("portfolio_images")),
            portfolio_missing_alt=_safe_int(img.get("portfolio_missing_alt")),
            contenido_multimedia=_safe_int(img.get("contenido_multimedia")),
        ),
        blog=BlogStats(
            total_posts=_safe_int(bl.get("total_posts")),
            posts_without_cover=_safe_int(bl.get("posts_without_cover")),
            posts_without_meta=_safe_int(bl.get("posts_without_meta")),
        ),
        portfolio=PortfolioStats(
            published=_safe_int(pf.get("published")),
        ),
    )


def parse_page_item(item: dict) -> SeoPage:
    """Map one /api/seo/keywords list item to a domain.SeoPage."""
    return SeoPage(
        url=_safe_str(item.get("url_path")),
        h1=_safe_str(item.get("keyword_h1")),
        h2=item.get("keyword_h2") or None,
        hero_title=item.get("hero_title") or None,
        meta_title=item.get("meta_title") or None,
        meta_description=item.get("meta_description") or None,
    )


def parse_pages_response(data: list) -> list[SeoPage]:
    """Map the /api/seo/keywords array to a list of SeoPage objects."""
    pages: list[SeoPage] = []
    for item in data or []:
        try:
            pages.append(parse_page_item(item))
        except Exception:
            logger.warning("Skipping malformed keyword item: %r", item)
    return pages


def build_update_payload(page: SeoPage) -> dict:
    """Build the JSON body for PUT /api/seo/keywords.

    All fields are sent even when None — the API performs a FULL REPLACE, so
    omitting an optional field CLEARS it in the DB. None values are sent as null.
    """
    return {
        "url_path": _canonicalize_url_path(page.url),
        "keyword_h1": page.h1,
        "keyword_h2": page.h2,
        "hero_title": page.hero_title,
        "meta_title": page.meta_title,
        "meta_description": page.meta_description,
    }


# ── adapter ───────────────────────────────────────────────────

class NoorCMSAdapter:
    """HTTP adapter for the Noor CMS SEO API.

    :param base_url: Root URL of the Noor instance, e.g. 'https://construccionesnoor.cloud'.
                     Trailing slashes are stripped automatically.
    :param api_key:  Value for the X-API-Key header.
    :param timeout:  httpx request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self._timeout = timeout

    # ── private helpers ───────────────────────────────────────

    def _get(self, path: str) -> httpx.Response:
        resp = httpx.get(
            f"{self._base}{path}",
            headers=self._headers,
            timeout=self._timeout,
        )
        self._raise_for_noor_errors(resp)
        return resp

    def _put(self, path: str, payload: dict) -> httpx.Response:
        resp = httpx.put(
            f"{self._base}{path}",
            headers=self._headers,
            json=payload,
            timeout=self._timeout,
        )
        self._raise_for_noor_errors(resp)
        return resp

    @staticmethod
    def _raise_for_noor_errors(resp: httpx.Response) -> None:
        """Translate Noor-specific HTTP error codes into clear domain exceptions."""
        if resp.status_code == 401:
            raise NoorCMSError(
                "Noor API key is missing or not configured on this request "
                "(HTTP 401). Check the X-API-Key header."
            )
        if resp.status_code == 403:
            raise NoorCMSError(
                "Noor API key was rejected (HTTP 403). "
                "Verify the key in Settings → Noor CMS."
            )
        if resp.status_code == 503:
            raise NoorCMSError(
                "Noor returned 503: its server either has no API key configured or is "
                "temporarily unavailable (deploying/overloaded). Check the Noor server."
            )
        if resp.status_code == 422:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise NoorCMSError(f"Noor rejected the request (HTTP 422): {detail}")
        # Any other non-2xx raises the httpx default
        resp.raise_for_status()

    # ── CMSPort interface ─────────────────────────────────────

    @staticmethod
    def _parse_json(resp: httpx.Response) -> object:
        """Parse the response body as JSON, raising NoorCMSError on decode failure."""
        try:
            return resp.json()
        except _json.JSONDecodeError:
            raise NoorCMSError(
                f"Noor returned a non-JSON response (HTTP {resp.status_code}) — "
                "the endpoint may be misconfigured or behind an error page."
            )

    def get_audit(self) -> SeoAudit:
        resp = self._get("/api/seo/audit")
        return parse_audit_response(self._parse_json(resp))

    def list_pages(self) -> list[SeoPage]:
        resp = self._get("/api/seo/keywords")
        return parse_pages_response(self._parse_json(resp))

    def update_page(self, page: SeoPage) -> dict:
        """Full-replace a page's SEO metadata in Noor.

        Canonicalises url_path and sends ALL fields so optional ones are not
        silently cleared by omission.
        """
        payload = build_update_payload(page)
        resp = self._put("/api/seo/keywords", payload)
        return self._parse_json(resp)

    def verify(self) -> None:
        """Probe /api/seo/audit — cheap connectivity + auth check.

        Returns None on success.  Propagates NoorCMSError on auth/HTTP failures
        and lets connection/timeout errors (httpx.RequestError) bubble up so the
        caller can build a meaningful error message.
        """
        self._get("/api/seo/audit")
