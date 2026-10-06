"""Persistence for SENSE signals. Idempotent upsert keyed by the unique tuple
so re-running a cycle never duplicates a day's data."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ...domain.models import QueryRanking, RankingSignal
from .models import RankingSignalRow


class RankingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
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

    def observed_range(self, site_url: str) -> tuple[date | None, date | None]:
        """First and last day with persisted signals for the site, or (None, None)."""
        with self._session_factory() as session:
            first, last = session.execute(
                select(
                    func.min(RankingSignalRow.observed_on),
                    func.max(RankingSignalRow.observed_on),
                ).where(RankingSignalRow.site_url == site_url)
            ).one()
            return first, last

    def summarize_by_query(
        self,
        site_url: str,
        start: date,
        end: date,
        limit: int | None = None,
        min_impressions: int = 0,
    ) -> list[QueryRanking]:
        """Aggregate [start, end] per query, most clicks first.

        Position is weighted by impressions, so a page seen once at position 90
        does not outweigh one seen a thousand times at position 3. Queries with
        fewer than ``min_impressions`` impressions in the window are dropped in
        SQL, before ``limit``, so the limit returns the top queries that qualify.
        """
        clicks = func.sum(RankingSignalRow.clicks)
        impressions = func.sum(RankingSignalRow.impressions)
        stmt = (
            select(
                RankingSignalRow.query,
                clicks,
                impressions,
                func.sum(RankingSignalRow.position * RankingSignalRow.impressions),
                func.avg(RankingSignalRow.position),
            )
            .where(
                RankingSignalRow.site_url == site_url,
                RankingSignalRow.observed_on >= start,
                RankingSignalRow.observed_on <= end,
            )
            .group_by(RankingSignalRow.query)
            .order_by(clicks.desc(), impressions.desc(), RankingSignalRow.query)
        )
        if min_impressions > 0:
            stmt = stmt.having(impressions >= min_impressions)
        if limit is not None:
            stmt = stmt.limit(limit)
        with self._session_factory() as session:
            rows = session.execute(stmt).all()
        result: list[QueryRanking] = []
        for query, total_clicks, total_impressions, weighted, plain_avg in rows:
            total_impressions = int(total_impressions or 0)
            position = (
                float(weighted) / total_impressions if total_impressions else float(plain_avg)
            )
            result.append(QueryRanking(
                query=query,
                clicks=int(total_clicks or 0),
                impressions=total_impressions,
                position=position,
            ))
        return result
