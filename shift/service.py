from __future__ import annotations

from datetime import datetime
from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Shift


def list_shifts(
    db: Session,
    *,
    org_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    ) -> list[Shift]:
    """
    Return shifts, optionally filtered by org and time window.

    Args:
        db: SQLAlchemy session.
        org_id: If provided, only shifts for this organization are returned.
        start: If provided, include shifts that *end after* this instant (overlap).
        end: If provided, include shifts that *start before* this instant (overlap).

    Returns:
        A list of 'Shift' ORM objects ordered by 'start_at'.
    """
    statement = select(Shift)

    if org_id is not None:
        statement = statement.where(Shift.org_id == org_id)
    if start is not None:
        statement = statement.where(Shift.end_at > start)
    if end is not None:
        statement = statement.where(Shift.start_at < end)

    statement = statement.order_by(Shift.start_at)
    return list(db.scalars(statement))
