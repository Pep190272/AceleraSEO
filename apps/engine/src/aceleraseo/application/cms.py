"""CMS on-page management use cases — read audit, list pages, update a page.

All validation that is about domain rules lives here (not in the adapter) so
the adapter can remain a thin HTTP translation layer.
"""
from __future__ import annotations

import re

from ..domain.models import SeoAudit, SeoPage
from ..domain.ports import CMSPort

# ── validation constants ──────────────────────────────────────

_H1_MIN_CHARS = 3
_H1_MAX_CHARS = 60


def _validate_h1(h1: str) -> None:
    """Raise ValueError with a user-friendly message when h1 violates Noor's rules.

    Checks applied (mirrors Noor's server-side validation so we surface a clear
    error before the HTTP call rather than a raw 422):
      - At least 3 non-whitespace characters.
      - No HTML angle brackets (< or >).
      - Maximum 60 characters.
    """
    # Strip all Unicode whitespace including \n, \r, \f, \v and non-breaking space
    # (\xa0). re.sub(r"[\s\xa0]+", "") covers both ASCII whitespace (\s) and NBSP.
    non_ws = re.sub(r"[\s\xa0]+", "", h1)
    if len(non_ws) < _H1_MIN_CHARS:
        raise ValueError(
            f"keyword_h1 must have at least {_H1_MIN_CHARS} non-whitespace characters "
            f"(got {len(non_ws)!r})."
        )
    if "<" in h1 or ">" in h1:
        raise ValueError("keyword_h1 must not contain HTML angle brackets (< or >).")
    if len(h1) > _H1_MAX_CHARS:
        raise ValueError(
            f"keyword_h1 must be at most {_H1_MAX_CHARS} characters "
            f"(got {len(h1)})."
        )


class GetSiteAudit:
    """Return the site-wide SEO health summary for the managed CMS site."""

    def __init__(self, cms: CMSPort) -> None:
        self._cms = cms

    def execute(self) -> SeoAudit:
        return self._cms.get_audit()


class ListSeoPages:
    """Return all pages managed by the CMS's SEO layer."""

    def __init__(self, cms: CMSPort) -> None:
        self._cms = cms

    def execute(self) -> list[SeoPage]:
        return self._cms.list_pages()


class UpdateSeoPage:
    """Full-replace a page's SEO metadata in the managed CMS.

    Validates domain rules before delegating to the adapter so the caller gets
    a clear ValueError rather than a raw HTTP 422 from the remote API.
    """

    def __init__(self, cms: CMSPort) -> None:
        self._cms = cms

    def execute(self, page: SeoPage) -> dict:
        _validate_h1(page.h1)
        return self._cms.update_page(page)
