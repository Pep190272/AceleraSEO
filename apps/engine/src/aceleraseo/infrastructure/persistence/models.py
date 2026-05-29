"""ORM rows. Time-series by design: one row per (site, query, page, date) so
LEARN can later diff position/clicks across cycles."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class RankingSignalRow(Base):
    __tablename__ = "ranking_signals"
    __table_args__ = (
        UniqueConstraint("site_url", "query", "page", "observed_on",
                         name="uq_ranking_signal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_url: Mapped[str] = mapped_column(String(512), index=True)
    query: Mapped[str] = mapped_column(String(2048))
    page: Mapped[str] = mapped_column(String(2048))
    position: Mapped[float] = mapped_column(Float)
    clicks: Mapped[int] = mapped_column(Integer)
    impressions: Mapped[int] = mapped_column(Integer)
    ctr: Mapped[float] = mapped_column(Float)
    observed_on: Mapped[date] = mapped_column(Date, index=True)
