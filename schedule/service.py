from __future__ import annotations
from datetime import date
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from .models import Schedule, ScheduleStatus
from .schema import ScheduleCreate

def get_schedules(
    db: Session,
    *,
    org_id: int,
    active_on: Optional[date] = None,
    start_from: Optional[date] = None,
    end_to: Optional[date] = None,
) -> List[Schedule]:
    stmt = select(Schedule).where(Schedule.org_id == org_id)
    if active_on is not None:
        stmt = stmt.where(and_(Schedule.range_start <= active_on, Schedule.range_end >= active_on))
    if start_from is not None:
        stmt = stmt.where(Schedule.range_start >= start_from)
    if end_to is not None:
        stmt = stmt.where(Schedule.range_end <= end_to)
    stmt = stmt.order_by(Schedule.range_start.desc(), Schedule.version.desc())
    return list(db.scalars(stmt))

def get_schedule_for_org(db: Session, schedule_id: int, org_id: int) -> Schedule | None:
    stmt = select(Schedule).where(Schedule.id == schedule_id, Schedule.org_id == org_id)
    return db.scalars(stmt).first()

def next_version_for_range(db: Session, *, org_id: int, start: date, end: date) -> int:
    maxv = db.scalar(
        select(func.max(Schedule.version)).where(
            Schedule.org_id == org_id, Schedule.range_start == start, Schedule.range_end == end
        )
    )
    return (maxv or 0) + 1

def create_schedule(db: Session, dto: ScheduleCreate) -> Schedule:
    if dto.range_start > dto.range_end:
        raise HTTPException(status_code=422, detail="start must be on or before end")

    version = dto.version or next_version_for_range(
        db, org_id=dto.org_id, start=dto.range_start, end=dto.range_end
    )

    row = Schedule(
        org_id=dto.org_id,
        range_start=dto.range_start,
        range_end=dto.range_end,
        version=version,
        created_by=dto.created_by,
        status=ScheduleStatus.draft,
        published_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def delete_schedule(db: Session, schedule_id: int) -> None:
    row = db.get(Schedule, schedule_id)
    if row:
        db.delete(row)
        db.commit()
