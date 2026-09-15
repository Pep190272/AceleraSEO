"""JS-rendering crawler adapter — implements domain.ports.PageFetcher.

For SPA / client-rendered sites the raw HTML has no links or content; the
HttpxCrawler is blind to them. This adapter drives a headless Chromium
(Playwright), waits for the DOM to settle, then hands the *rendered* HTML to
the SAME parse_html() used by the plain crawler. Audit rules and traversal are
untouched — that is the whole point of the PageFetcher port.

Playwright is an optional dependency:
    pip install -e ".[render]" && playwright install chromium
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ...domain.models import CrawledPage
from .crawler import parse_html
from .url_safety import UnsafeURLError, ensure_public_url

if TYPE_CHECKING:
    from playwright.sync_api import Request, Response, Route

_DEFAULT_UA = "AceleraSEO-Crawler/0.1 (+https://github.com/Pep190272/AceleraSEO)"


class RenderingCrawler:
    """Headless-Chromium fetcher. Reuses one browser across fetches for speed."""

    def __init__(self, timeout: float = 20.0, wait_until: str = "networkidle"):
        # Import here so the package import stays cheap and Playwright stays optional.
        from playwright.sync_api import sync_playwright

        self._timeout_ms = int(timeout * 1000)
        self._wait_until = wait_until
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        # Service workers can serve requests that never reach context.route().
        self._context = self._browser.new_context(user_agent=_DEFAULT_UA, service_workers="block")
        self._context.route("**/*", block_private_requests)

    def fetch(self, url: str) -> CrawledPage:
        page = self._context.new_page()
        try:
            resp = page.goto(url, timeout=self._timeout_ms, wait_until=self._wait_until)
            status = resp.status if resp else 0
            if resp and not redirect_chain_is_public(resp):
                return CrawledPage(url=url, status_code=0)  # redirected to a private host
            html = page.content()
        except Exception:
            return CrawledPage(url=url, status_code=0)  # unreachable / render failure
        finally:
            page.close()
        return parse_html(url, status, html)

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._pw.stop()


def block_private_requests(route: Route) -> None:
    """Abort any browser request (page, subresource, fetch) to a non-public host.

    Playwright does not call route handlers for redirect hops; fetch() checks the
    redirect chain afterwards and discards the page (redirect_chain_is_public).
    WebSocket connections do not pass through here and are not checked.
    """
    url = route.request.url
    if urlsplit(url).scheme in ("http", "https"):
        try:
            ensure_public_url(url)
        except UnsafeURLError:
            route.abort()
            return
    route.continue_()


def redirect_chain_is_public(resp: Response) -> bool:
    """True when every hop that led to this response was a public http(s) URL.

    The browser has already made the redirected request by the time this runs, so
    it stops the private response from reaching the audit, not the request itself.
    """
    request: Request | None = resp.request
    while request is not None:
        try:
            ensure_public_url(request.url)
        except UnsafeURLError:
            return False
        request = request.redirected_from
    return True
