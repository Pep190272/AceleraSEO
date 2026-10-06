"""Persistence for SENSE signals. Idempotent upsert keyed by the unique tuple
so re-running a cycle never duplicates a day's data."""
from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from ...domain.models import ConversionCount, ConversionSnapshot, QueryRanking, RankingSignal
from .models import ConversionSignalRow, RankingSignalRow

# A collection that found no conversions is stored as this one zero row, so it still
# supersedes the previous snapshot instead of leaving it on screen.
_EMPTY_MARKER = ConversionCount(path="/", type="_empty", count=0)


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

    def top_pages(
        self, site_url: str, start: date, end: date, queries: list[str]
    ) -> dict[str, str]:
        """The page with most clicks (then impressions) per query in [start, end]."""
        if not queries:
            return {}
        clicks = func.sum(RankingSignalRow.clicks)
        impressions = func.sum(RankingSignalRow.impressions)
        stmt = (
            select(RankingSignalRow.query, RankingSignalRow.page)
            .where(
                RankingSignalRow.site_url == site_url,
                RankingSignalRow.observed_on >= start,
                RankingSignalRow.observed_on <= end,
                RankingSignalRow.query.in_(queries),
            )
            .group_by(RankingSignalRow.query, RankingSignalRow.page)
            .order_by(RankingSignalRow.query, clicks.desc(), impressions.desc(),
                      RankingSignalRow.page)
        )
        with self._session_factory() as session:
            rows = session.execute(stmt).all()
        result: dict[str, str] = {}
        for query, page in rows:
            result.setdefault(query, page)
        return result

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


class ConversionRepository:
    """Conversion snapshots, one per (site, window end)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_snapshot(self, site_url: str, snapshot: ConversionSnapshot) -> int:
        """Idempotent upsert: replace the site's rows for ``snapshot.window_end``.

        Re-running a collection on the same day overwrites that day's counts in one
        transaction, and a path that dropped out of the source does not linger.
        Returns the number of conversion rows stored.
        """
        rows = snapshot.rows or [_EMPTY_MARKER]
        with self._session_factory() as session:
            session.execute(
                delete(ConversionSignalRow).where(
                    ConversionSignalRow.site_url == site_url,
                    ConversionSignalRow.window_end == snapshot.window_end,
                )
            )
            session.add_all(
                ConversionSignalRow(
                    site_url=site_url, path=row.path, type=row.type,
                    window_end=snapshot.window_end, window_days=snapshot.window_days,
                    count=row.count,
                )
                for row in rows
            )
            session.commit()
        return len(snapshot.rows)

    def latest_snapshot(self, site_url: str) -> ConversionSnapshot | None:
        """The most recent collection for the site, or None if there is none."""
        with self._session_factory() as session:
            end = session.scalar(
                select(func.max(ConversionSignalRow.window_end)).where(
                    ConversionSignalRow.site_url == site_url
                )
            )
            if end is None:
                return None
            rows = session.scalars(
                select(ConversionSignalRow).where(
                    ConversionSignalRow.site_url == site_url,
                    ConversionSignalRow.window_end == end,
                )
            ).all()
        return ConversionSnapshot(
            window_end=end,
            window_days=max(r.window_days for r in rows),
            rows=[ConversionCount(r.path, r.type, r.count)
                  for r in rows if r.type != _EMPTY_MARKER.type],
        )
