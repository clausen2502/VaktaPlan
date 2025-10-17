from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException, status


from .models import Shift, ShiftStatus
from .schemas import ShiftCreateIn, ShiftUpdateIn

def get_shift(db: Session, shift_id: int) -> Shift:
    """
    Get a single shift by id.
    """
    return db.query(Shift).filter(Shift.id == shift_id).first()

def get_shifts(
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

def create_shift(db: Session, shift: ShiftCreateIn) -> Shift:
    """
    Create a new Shift.
    """
    db_shift = Shift(
        org_id=shift.org_id,
        location_id=shift.location_id,
        role_id=shift.role_id,
        start_at=shift.start_at,
        end_at=shift.end_at,
        status=shift.status,
        notes=shift.notes,
    )
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

def delete_shift(db: Session, shift_id: int) -> None:
    """
    Delete shifts by id.
    """
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if db_shift:
        db.delete(db_shift)
        db.commit()
    return

def update_shift(db: Session, shift_id: int, patch: ShiftUpdateIn) -> Shift:
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    data = patch.model_dump(exclude_unset=True, exclude_none=True)
    new_start = data.get("start_at", db_shift.start_at)
    new_end   = data.get("end_at",   db_shift.end_at)

    # validation
    if new_start is not None and new_end is not None and new_start >= new_end:
        raise HTTPException(status_code=422, detail="start_at must be before end_at")

    for k, v in data.items():
        setattr(db_shift, k, v)

    db.commit()
    db.refresh(db_shift)
    return db_shift
