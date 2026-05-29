"""URL Inspection adapter — implements domain.ports.IndexStatusReader.

READ-ONLY (verified — docs/API-LIMITS.md): Google offers no programmatic way to
REQUEST indexing for normal pages. We can only ASK whether a URL is indexed and
alert when it isn't. This monitors; it never forces.
"""
from __future__ import annotations

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ...domain.models import IndexStatus

# verdict == "PASS" means the URL is on Google.
_INDEXED_VERDICTS = {"PASS"}


class URLInspectionReader:
    def __init__(self, credentials: Credentials, site_url: str):
        self._service = build("searchconsole", "v1", credentials=credentials,
                              cache_discovery=False)
        self._site_url = site_url

    def is_indexed(self, url: str) -> bool:
        return self.inspect(url).indexed

    def inspect(self, url: str) -> IndexStatus:
        body = {"inspectionUrl": url, "siteUrl": self._site_url}
        resp = self._service.urlInspection().index().inspect(body=body).execute()
        verdict = (
            resp.get("inspectionResult", {})
            .get("indexStatusResult", {})
            .get("verdict", "")
        )
        return IndexStatus(url=url, indexed=verdict in _INDEXED_VERDICTS)
