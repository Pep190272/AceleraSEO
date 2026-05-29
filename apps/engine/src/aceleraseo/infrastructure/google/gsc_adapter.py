"""Google Search Console adapter — implements domain.ports.RankingProvider.

Pulls real ranking performance (clicks, impressions, position, CTR) per
query+page from the Search Analytics API. This is the SENSE signal Ahrefs
never has: how YOUR site actually performs in Google.
"""
from __future__ import annotations

from datetime import date, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ...domain.models import RankingSignal

# GSC data lags ~2-3 days; the API caps at 25k rows per request.
_GSC_LAG_DAYS = 3
_ROW_LIMIT = 25_000


class GSCRankingProvider:
    def __init__(self, credentials: Credentials):
        self._service = build("searchconsole", "v1", credentials=credentials,
                              cache_discovery=False)

    def fetch_rankings(self, site_url: str, days: int) -> list[RankingSignal]:
        end = date.today() - timedelta(days=_GSC_LAG_DAYS)
        start = end - timedelta(days=days)
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query", "page", "date"],
            "rowLimit": _ROW_LIMIT,
        }
        resp = (
            self._service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )
        return [_to_signal(row) for row in resp.get("rows", [])]


def _to_signal(row: dict) -> RankingSignal:
    query, page, observed = row["keys"]
    return RankingSignal(
        query=query,
        page=page,
        position=float(row.get("position", 0.0)),
        clicks=int(row.get("clicks", 0)),
        impressions=int(row.get("impressions", 0)),
        ctr=float(row.get("ctr", 0.0)),
        observed_on=date.fromisoformat(observed),
    )
