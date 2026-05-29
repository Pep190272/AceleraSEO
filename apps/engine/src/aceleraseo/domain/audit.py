"""Audit rules — pure functions over a CrawledPage. No I/O, fully testable.

Each rule cites WHY it matters: a finding the user can't understand is a finding
they won't act on. Severity reflects SEO impact, not cosmetic preference.
"""
from __future__ import annotations

from .models import AuditIssue, CrawledPage, Severity

_TITLE_MAX = 60          # px-equivalent char budget before SERP truncation
_TITLE_MIN = 10
_DESC_MAX = 160
_THIN_CONTENT = 200      # words; below this a page rarely satisfies intent


def audit_page(page: CrawledPage) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    def add(code: str, severity: Severity, message: str) -> None:
        issues.append(AuditIssue(code=code, severity=severity, url=page.url, message=message))

    # Reachability — a broken page ranks for nothing.
    if page.status_code >= 500:
        add("server_error", Severity.CRITICAL, f"Server error {page.status_code}.")
        return issues  # nothing else to audit on a dead page
    if page.status_code >= 400:
        add("broken_page", Severity.CRITICAL, f"Page returns {page.status_code} (not found / gone).")
        return issues

    # Indexability — noindex silently removes the page from Google.
    if page.robots_noindex:
        add("noindex", Severity.CRITICAL,
            "Page is noindex — it cannot rank. Remove the directive if this is wrong.")

    # Title.
    if not page.title:
        add("missing_title", Severity.WARNING, "Missing <title> — the #1 on-page ranking element.")
    else:
        n = len(page.title)
        if n > _TITLE_MAX:
            add("title_too_long", Severity.NOTICE,
                f"Title {n} chars — Google truncates around {_TITLE_MAX}.")
        elif n < _TITLE_MIN:
            add("title_too_short", Severity.NOTICE, f"Title only {n} chars — likely too thin.")

    # Meta description — drives CTR, not ranking directly.
    if not page.meta_description:
        add("missing_meta_description", Severity.WARNING,
            "Missing meta description — hurts click-through rate from the SERP.")
    elif len(page.meta_description) > _DESC_MAX:
        add("meta_description_too_long", Severity.NOTICE,
            f"Meta description {len(page.meta_description)} chars — truncated past {_DESC_MAX}.")

    # Headings.
    if len(page.h1s) == 0:
        add("missing_h1", Severity.WARNING, "No <h1> — weakens topical signal.")
    elif len(page.h1s) > 1:
        add("multiple_h1", Severity.NOTICE, f"{len(page.h1s)} <h1> tags — keep one primary heading.")

    # Canonical — prevents duplicate-content dilution.
    if not page.canonical:
        add("missing_canonical", Severity.NOTICE,
            "No canonical URL — risk of duplicate-content dilution.")

    # Content depth.
    if page.word_count < _THIN_CONTENT:
        add("thin_content", Severity.NOTICE,
            f"Only {page.word_count} words — thin content rarely satisfies search intent.")

    # Structured data.
    if not page.has_schema:
        add("missing_schema", Severity.NOTICE,
            "No structured data (schema.org) — missing rich-result eligibility.")

    return issues
