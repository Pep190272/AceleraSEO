from aceleraseo.domain.audit import audit_page
from aceleraseo.domain.models import CrawledPage, Severity


def _codes(issues):
    return {i.code for i in issues}


def healthy_page():
    return CrawledPage(
        url="https://x.com/p",
        status_code=200,
        title="A good honest title for ranking",
        meta_description="A concise compelling description that fits the SERP nicely.",
        h1s=("Main heading",),
        canonical="https://x.com/p",
        internal_links=(),
        word_count=500,
        has_schema=True,
        robots_noindex=False,
    )


def test_healthy_page_has_no_issues():
    assert audit_page(healthy_page()) == []


def test_broken_page_is_critical_and_short_circuits():
    issues = audit_page(CrawledPage(url="https://x.com/404", status_code=404))
    assert _codes(issues) == {"broken_page"}
    assert issues[0].severity is Severity.CRITICAL


def test_noindex_is_critical():
    page = healthy_page().__class__(**{**healthy_page().__dict__, "robots_noindex": True})
    assert "noindex" in _codes(audit_page(page))


def test_missing_title_and_meta_are_warnings():
    base = healthy_page().__dict__
    page = CrawledPage(**{**base, "title": None, "meta_description": None})
    issues = audit_page(page)
    codes = _codes(issues)
    assert "missing_title" in codes
    assert "missing_meta_description" in codes
    sev = {i.code: i.severity for i in issues}
    assert sev["missing_title"] is Severity.WARNING


def test_thin_content_and_missing_schema_are_notices():
    base = healthy_page().__dict__
    page = CrawledPage(**{**base, "word_count": 50, "has_schema": False})
    sev = {i.code: i.severity for i in audit_page(page)}
    assert sev["thin_content"] is Severity.NOTICE
    assert sev["missing_schema"] is Severity.NOTICE
