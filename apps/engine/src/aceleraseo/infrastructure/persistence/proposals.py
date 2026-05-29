"""Proposal queue — persisted actions awaiting human approval (ADR-0002).

Every action the agent would take when not auto-executing lands here with full
context (kind, target, risk, rationale) so a human can approve/reject in the
dashboard. Auditable + reversible by design.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ...domain.models import Action
from .db import Base


class ProposalRow(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64))
    target_url: Mapped[str] = mapped_column(String(2048))
    description: Mapped[str] = mapped_column(String(2048))
    risk: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProposalRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def enqueue(self, action: Action) -> int:
        with self._session_factory() as session:
            row = ProposalRow(
                kind=action.kind,
                target_url=action.target_url,
                description=action.description,
                risk=action.risk,
                rationale=action.rationale,
            )
            session.add(row)
            session.commit()
            return row.id

    def pending(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProposalRow).where(ProposalRow.status == "pending")
            ).all()
            return [_to_dict(r) for r in rows]

    def set_status(self, proposal_id: int, status: str) -> bool:
        with self._session_factory() as session:
            row = session.get(ProposalRow, proposal_id)
            if row is None:
                return False
            row.status = status
            session.commit()
            return True


def _to_dict(r: ProposalRow) -> dict:
    return {
        "id": r.id, "kind": r.kind, "target_url": r.target_url,
        "description": r.description, "risk": r.risk, "rationale": r.rationale,
        "status": r.status,
    }
