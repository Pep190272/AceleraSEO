"""IndexNow adapter — implements domain.ports.Indexer.

Instant indexing on Bing, Yandex, Naver, Seznam, Yep. Google does NOT support
IndexNow (verified — docs/API-LIMITS.md), so this never touches Google; for
Google we rely on sitemaps + the URL Inspection monitor.

Protocol: POST the key + a list of URLs to a single endpoint; participating
engines fan it out. The payload builder is a pure function for testing.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

_ENDPOINT = "https://api.indexnow.org/indexnow"


class IndexNowIndexer:
    def __init__(self, key: str, key_location: str, timeout: float = 15.0):
        self._key = key
        self._key_location = key_location
        self._timeout = timeout

    def submit(self, urls: list[str]) -> bool:
        if not urls or not self._key:
            return False
        host = _host_of(urls[0])
        payload = build_payload(host, self._key, self._key_location, urls)
        resp = httpx.post(_ENDPOINT, json=payload, timeout=self._timeout)
        # IndexNow returns 200/202 on accept.
        return resp.status_code in (200, 202)


def build_payload(host: str, key: str, key_location: str, urls: list[str]) -> dict:
    payload = {"host": host, "key": key, "urlList": urls}
    if key_location:
        payload["keyLocation"] = key_location
    return payload


def _host_of(url: str) -> str:
    return urlparse(url).netloc
