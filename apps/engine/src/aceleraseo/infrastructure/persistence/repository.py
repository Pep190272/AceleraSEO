"""Persistence for SENSE signals. Idempotent upsert keyed by the unique tuple
so re-running a cycle never duplicates a day's data."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ...domain.models import RankingSignal
from .models import RankingSignalRow


class RankingRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_many(self, site_url: str, signals: list[RankingSignal]) -> int:
        """Upsert signals. Returns number of new rows inserted."""
        inserted = 0
        with self._session_factory() as session:
            for sig in signals:
                exists = session.scalar(
                    select(RankingSignalRow.id).where(
                        RankingSignalRow.site_url == site_url,
                        RankingSignalRow.query == sig.query,
                        RankingSignalRow.page == sig.page,
                        RankingSignalRow.observed_on == sig.observed_on,
                    )
                )
                if exists:
                    continue
                session.add(RankingSignalRow(
                    site_url=site_url,
                    query=sig.query,
                    page=sig.page,
                    position=sig.position,
                    clicks=sig.clicks,
                    impressions=sig.impressions,
                    ctr=sig.ctr,
                    observed_on=sig.observed_on,
                ))
                inserted += 1
            session.commit()
        return inserted

    def fetch_window(
        self, site_url: str, start: date, end: date
    ) -> list[RankingSignal]:
        """Read persisted signals in [start, end] — feeds the LEARN comparison."""
        with self._session_factory() as session:
            rows = session.scalars(
                select(RankingSignalRow).where(
                    RankingSignalRow.site_url == site_url,
                    RankingSignalRow.observed_on >= start,
                    RankingSignalRow.observed_on <= end,
                )
            ).all()
            return [
                RankingSignal(
                    query=r.query, page=r.page, position=r.position,
                    clicks=r.clicks, impressions=r.impressions, ctr=r.ctr,
                    observed_on=r.observed_on,
                )
                for r in rows
            ]
