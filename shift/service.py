from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from .models import Shift
from .schemas import ShiftCreate, ShiftUpdate

def get_shift(db: Session, shift_id: int) -> Shift | None:
    return db.get(Shift, shift_id)

def get_shifts(
    db: Session,
    *,
    org_id: Optional[int] = None,
    schedule_id: Optional[int] = None,
    location_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> list[Shift]:
    stmt = select(Shift)
    if org_id is not None:
        stmt = stmt.where(Shift.org_id == org_id)
    if schedule_id is not None:
        stmt = stmt.where(Shift.schedule_id == schedule_id)
    if location_id is not None:
        stmt = stmt.where(Shift.location_id == location_id)
    if start is not None:
        stmt = stmt.where(Shift.end_at > start)   # overlaps window
    if end is not None:
        stmt = stmt.where(Shift.start_at < end)   # overlaps window
    if notes is not None:
        stmt = stmt.where(Shift.notes.ilike(f"%{notes}%"))
    stmt = stmt.order_by(Shift.start_at)
    return list(db.scalars(stmt))

def create_shift(db: Session, shift: ShiftCreate) -> Shift:
    row = Shift(
        org_id=shift.org_id,
        schedule_id=shift.schedule_id,
        location_id=shift.location_id,
        role_id=shift.role_id,
        start_at=shift.start_at,
        end_at=shift.end_at,
        notes=shift.notes,
    )
    if row.start_at >= row.end_at:
        raise HTTPException(status_code=422, detail="start_at must be before end_at")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def update_shift(db: Session, shift_id: int, patch: ShiftUpdate) -> Shift:
    row = db.get(Shift, shift_id)
    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")

    data = patch.model_dump(exclude_unset=True)
    new_start = data.get("start_at", row.start_at)
    new_end   = data.get("end_at",   row.end_at)
    if new_start is not None and new_end is not None and new_start >= new_end:
        raise HTTPException(status_code=422, detail="start_at must be before end_at")

    for k, v in data.items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return row

def delete_shift(db: Session, shift_id: int) -> None:
    row = db.get(Shift, shift_id)
    if row:
        db.delete(row)
        db.commit()

def get_shift_for_org(db: Session, shift_id: int, org_id: int) -> Optional[Shift]:
    stmt = select(Shift).where(Shift.id == shift_id, Shift.org_id == org_id)
    return db.scalars(stmt).first()
