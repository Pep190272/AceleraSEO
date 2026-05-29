from aceleraseo.application.crawl import CrawlSite
from aceleraseo.domain.models import CrawledPage
from aceleraseo.infrastructure.providers.crawler import parse_html


class FakeFetcher:
    """Serves canned pages forming a small link graph — no network."""
    def __init__(self, pages: dict[str, CrawledPage]):
        self._pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str) -> CrawledPage:
        self.calls.append(url)
        return self._pages.get(url, CrawledPage(url=url, status_code=404))


def _page(url, links=(), status=200):
    return CrawledPage(url=url, status_code=status, title="t" * 20,
                       meta_description="d" * 30, h1s=("h",), canonical=url,
                       internal_links=tuple(links), word_count=300, has_schema=True)


def test_crawl_stays_on_host_and_dedups():
    pages = {
        "https://site.com": _page("https://site.com",
                                  links=["https://site.com/a",
                                         "https://site.com/a",          # dup
                                         "https://external.com/x"]),    # off-host
        "https://site.com/a": _page("https://site.com/a", links=["https://site.com"]),
    }
    fetcher = FakeFetcher(pages)
    report = CrawlSite(fetcher).execute("https://site.com")
    crawled = {p.url for p in report.pages}
    assert crawled == {"https://site.com", "https://site.com/a"}
    assert "https://external.com/x" not in fetcher.calls


def test_crawl_respects_max_pages():
    pages = {f"https://site.com/{i}": _page(f"https://site.com/{i}",
             links=[f"https://site.com/{i+1}"]) for i in range(10)}
    pages["https://site.com"] = _page("https://site.com", links=["https://site.com/0"])
    report = CrawlSite(FakeFetcher(pages)).execute("https://site.com", max_pages=3)
    assert len(report.pages) == 3


def test_crawl_aggregates_issues_from_broken_pages():
    pages = {"https://site.com": _page("https://site.com",
                                       links=["https://site.com/dead"]),
             "https://site.com/dead": _page("https://site.com/dead", status=500)}
    report = CrawlSite(FakeFetcher(pages)).execute("https://site.com")
    assert any(i.code == "server_error" for i in report.issues)


def test_parse_html_extracts_signals():
    html = """
    <html><head>
      <title>Hello World Page</title>
      <meta name="description" content="A description">
      <meta name="robots" content="noindex,follow">
      <link rel="canonical" href="https://site.com/canonical">
      <script type="application/ld+json">{}</script>
    </head><body>
      <h1>First</h1><h1>Second</h1>
      <a href="/internal">in</a>
      <a href="https://other.com/x">out</a>
      <p>some words here in the body content</p>
    </body></html>
    """
    page = parse_html("https://site.com/p", 200, html)
    assert page.title == "Hello World Page"
    assert page.meta_description == "A description"
    assert page.robots_noindex is True
    assert page.canonical == "https://site.com/canonical"
    assert len(page.h1s) == 2
    assert "https://site.com/internal" in page.internal_links
    assert "https://other.com/x" in page.external_links
    assert page.has_schema is True
    assert page.word_count > 0
