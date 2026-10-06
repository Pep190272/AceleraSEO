"""First-party conversions read from the site's own WordPress endpoint.

Implements domain.ports.AnalyticsProvider without a client-side tag or cookies:
the site records its leads server-side and serves aggregated counts. The contract
is fixed in docs/plans/first-party-conversions.md:

    GET <endpoint>?days=<1..480>   with header X-API-Key: <key>
    200 -> {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD",
            "rows": [{"path": "/a/", "type": "form", "count": 2}, ...]}
    401 -> missing or wrong key, 422 -> days out of range
"""
from __future__ import annotations

from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from ...domain.models import ConversionCount, ConversionSnapshot
from ...domain.paths import normalize_path

__all__ = ["WordPressConversionsError", "WordPressConversionsProvider", "normalize_path"]

WP_CONVERSIONS_TIMEOUT_SECONDS = 30.0


class WordPressConversionsError(Exception):
    """The endpoint failed or answered outside the contract.

    status_code is the HTTP status the API surface should answer with.
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConversionRow(BaseModel):
    path: str
    type: str
    # Strict: JSON true or "2" is outside the contract, not a count.
    count: StrictInt = Field(ge=0)


class ConversionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: date = Field(alias="from")
    to: date
    rows: list[ConversionRow]



class WordPressConversionsProvider:
    """HTTP adapter for the site's conversions endpoint (pattern: providers/noor.py)."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        timeout: float = WP_CONVERSIONS_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = endpoint_url
        self._headers = {"X-API-Key": api_key, "Accept": "application/json"}
        self._timeout = timeout
        self._transport = transport

    def fetch_conversions(self, property_id: str, days: int) -> dict[str, float]:
        """Return {normalised path: conversions of every type} for the window.

        property_id is a GA4 concept; the endpoint URL already identifies the site.
        """
        totals = self.fetch_conversion_rows(days).totals()
        return {path: float(count) for path, count in totals.items()}

    def fetch_conversion_rows(self, days: int) -> ConversionSnapshot:
        """Counts per normalised path and type, for the window the endpoint reported.

        '/a' and '/a/' normalise to one path, so their counts are merged per type.
        """
        body = self._get(days)
        counts: dict[tuple[str, str], int] = {}
        for row in body.rows:
            key = (normalize_path(row.path), row.type)
            counts[key] = counts.get(key, 0) + row.count
        return ConversionSnapshot(
            window_end=body.to,
            window_days=(body.to - body.from_).days + 1,
            rows=[ConversionCount(path, kind, count) for (path, kind), count in counts.items()],
        )

    def _get(self, days: int) -> ConversionsResponse:
        try:
            with httpx.Client(
                timeout=self._timeout, transport=self._transport, follow_redirects=False
            ) as client:
                resp = client.get(self._url, params={"days": days}, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise WordPressConversionsError(
                "The WordPress conversions endpoint did not answer in time.", 504
            ) from exc
        except httpx.RequestError as exc:
            raise WordPressConversionsError(
                "Could not reach the WordPress conversions endpoint. Check the URL.", 502
            ) from exc

        if 300 <= resp.status_code < 400:
            # Redirects are not followed: the key must not travel to another URL.
            raise WordPressConversionsError(
                f"The WordPress conversions endpoint redirected (HTTP {resp.status_code}). "
                "Set its final URL in Settings > Conversions (check https and the "
                "trailing slash).",
                502,
            )
        if resp.status_code in (401, 403):
            raise WordPressConversionsError(
                "WordPress rejected the API key. Check it in Settings > Conversions.", 502
            )
        if resp.status_code == 422:
            raise WordPressConversionsError(
                "WordPress rejected the request (HTTP 422): the days window is out of range.",
                502,
            )
        if resp.status_code == 429:
            raise WordPressConversionsError(
                "The WordPress conversions endpoint is rate limiting. Try again shortly.", 429
            )
        if resp.status_code != 200:
            raise WordPressConversionsError(
                f"The WordPress conversions endpoint answered HTTP {resp.status_code}.", 502
            )
        try:
            return ConversionsResponse.model_validate_json(resp.content)
        except ValidationError as exc:
            raise WordPressConversionsError(
                "The WordPress conversions endpoint returned a body outside the contract.", 502
            ) from exc
