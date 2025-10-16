from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from .models import Shift, ShiftStatus
from .schemas import ShiftCreateIn


def list_shifts(
    db: Session,
    *,
    org_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status: Optional[ShiftStatus] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
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
    if location_id is not None:
        statement = statement.where(Shift.location_id == location_id)
    if status is not None:
        statement = statement.where(Shift.status == status)
    if start is not None:
        statement = statement.where(Shift.end_at > start)
    if end is not None:
        statement = statement.where(Shift.start_at < end)
    if notes is not None:
        statement = statement.where(Shift.notes.ilike(f"%{notes}%"))
    statement = statement.order_by(Shift.start_at)
    return list(db.scalars(statement))

def create_shift(db: Session, payload: ShiftCreateIn) -> Shift:
    shift_obj = Shift(
        org_id=payload.org_id,
        location_id=payload.location_id,
        role_id=payload.role_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(shift_obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Constraint failed")
    db.refresh(shift_obj)
    return shift_obj