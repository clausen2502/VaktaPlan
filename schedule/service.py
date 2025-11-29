from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from .models import Schedule, ScheduleStatus
from .schema import ScheduleCreate, ScheduleUpdate

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
        name=dto.name,
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

def publish_schedule(db: Session, *,schedule_id: int, org_id: int,) -> Schedule:
    """
    Mark a schedule as published for the given org.
    - 404 if schedule not found or belongs to another org
    - if it is already published, just return it
    """
    sched = db.get(Schedule, schedule_id)
    if not sched or sched.org_id != org_id:
        raise HTTPException(status_code=404, detail="schedule not found")

    if sched.status != ScheduleStatus.published:
        sched.status = ScheduleStatus.published
        sched.published_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(sched)

    return sched

def update_schedule(
    db: Session,
    schedule_id: int,
    patch: ScheduleUpdate,
    ) -> Schedule:
    db_sched = db.get(Schedule, schedule_id)
    if not db_sched:
        raise HTTPException(status_code=404, detail="schedule not found")

    data = patch.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(db_sched, k, v)
    db.commit()
    db.refresh(db_sched)
    return db_sched

