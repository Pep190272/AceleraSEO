"""CRAWL use case — BFS over a site, audit every page, aggregate a report.

Depends only on the PageFetcher port, so the whole traversal (same-host filter,
dedup, depth/page caps) is testable with a fake fetcher — no network.
"""
from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urlparse

from ..domain.audit import audit_page
from ..domain.models import CrawlReport
from ..domain.ports import PageFetcher


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _normalize(url: str) -> str:
    # Drop fragments so /a and /a#section aren't crawled twice.
    return urldefrag(url)[0].rstrip("/") or url


class CrawlSite:
    def __init__(self, fetcher: PageFetcher):
        self._fetcher = fetcher

    def execute(
        self,
        start_url: str,
        max_pages: int = 500,
        max_depth: int = 5,
    ) -> CrawlReport:
        start = _normalize(start_url)
        origin_host = _host(start)

        report = CrawlReport()
        seen: set[str] = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])

        while queue and len(report.pages) < max_pages:
            url, depth = queue.popleft()
            page = self._fetcher.fetch(url)
            report.pages.append(page)
            report.issues.extend(audit_page(page))

            if depth >= max_depth:
                continue

            for link in page.internal_links:
                nxt = _normalize(link)
                if nxt in seen:
                    continue
                if _host(nxt) != origin_host:   # stay on the same site
                    continue
                seen.add(nxt)
                queue.append((nxt, depth + 1))

        return report
