"""HTTP crawler adapter — implements domain.ports.PageFetcher.

Fetches a URL with httpx and parses the HTML (selectolax) into a CrawledPage.
Parsing lives here (I/O detail); the audit rules stay pure in the domain.
"""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from ...domain.models import CrawledPage

_DEFAULT_HEADERS = {"User-Agent": "AceleraSEO-Crawler/0.1 (+https://github.com/Pep190272/AceleraSEO)"}


class HttpxCrawler:
    def __init__(self, timeout: float = 10.0, follow_redirects: bool = True):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=follow_redirects,
            headers=_DEFAULT_HEADERS,
        )

    def fetch(self, url: str) -> CrawledPage:
        try:
            resp = self._client.get(url)
        except httpx.RequestError:
            return CrawledPage(url=url, status_code=0)  # unreachable

        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type:
            return CrawledPage(url=url, status_code=resp.status_code)

        return parse_html(url, resp.status_code, resp.text)

    def close(self) -> None:
        self._client.close()


def parse_html(url: str, status_code: int, html: str) -> CrawledPage:
    """Pure-ish parser (no network) — separated so it can be unit-tested directly."""
    tree = HTMLParser(html)
    base_host = urlparse(url).netloc.lower()

    title_node = tree.css_first("title")
    title = title_node.text(strip=True) if title_node else None

    meta_desc = _meta(tree, "description")
    robots = (_meta(tree, "robots") or "").lower()

    canonical_node = tree.css_first('link[rel="canonical"]')
    canonical = canonical_node.attributes.get("href") if canonical_node else None

    h1s = tuple(n.text(strip=True) for n in tree.css("h1") if n.text(strip=True))

    internal: list[str] = []
    external: list[str] = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href") or ""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(url, href)
        if urlparse(absolute).netloc.lower() == base_host:
            internal.append(absolute)
        else:
            external.append(absolute)

    body = tree.css_first("body")
    word_count = len(body.text(separator=" ", strip=True).split()) if body else 0

    has_schema = bool(
        tree.css_first('script[type="application/ld+json"]')
        or tree.css_first("[itemscope]")
    )

    return CrawledPage(
        url=url,
        status_code=status_code,
        title=title,
        meta_description=meta_desc,
        h1s=h1s,
        canonical=canonical,
        internal_links=tuple(dict.fromkeys(internal)),  # dedup, keep order
        external_links=tuple(dict.fromkeys(external)),
        word_count=word_count,
        has_schema=has_schema,
        robots_noindex="noindex" in robots,
    )


def _meta(tree: HTMLParser, name: str) -> str | None:
    node = tree.css_first(f'meta[name="{name}"]')
    return node.attributes.get("content") if node else None
