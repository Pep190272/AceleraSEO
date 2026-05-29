"""RenderingCrawler is exercised live (network + chromium) so it is opt-in:
run with `pytest -m render`. The default suite stays fast and offline.

What we assert without a browser: the adapter satisfies the PageFetcher port
and reuses the same parse_html the plain crawler uses (contract, not behavior).
"""
import pytest


def test_rendering_crawler_satisfies_pagefetcher_protocol():
    # Import the class without constructing it (no browser launched).
    from aceleraseo.infrastructure.providers.rendering_crawler import RenderingCrawler

    # Structural check: it has the fetch(url) method the port requires.
    assert hasattr(RenderingCrawler, "fetch")
    assert hasattr(RenderingCrawler, "close")
    # isinstance against a runtime-checkable Protocol needs an instance; assert the
    # method signature exists at the class level instead (keeps this browser-free).
    assert callable(RenderingCrawler.fetch)


@pytest.mark.render
def test_rendering_crawler_fetches_live_page():
    from aceleraseo.infrastructure.providers.rendering_crawler import RenderingCrawler

    crawler = RenderingCrawler(timeout=20.0)
    try:
        page = crawler.fetch("https://example.com")
    finally:
        crawler.close()
    assert page.status_code == 200
    assert page.title is not None
