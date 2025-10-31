from __future__ import annotations
from datetime import datetime, timedelta, date, time, timezone
from typing import Optional, Iterable

from fastapi import HTTPException
from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import WeeklyTemplate
from .schema import (
    WeeklyTemplateUpsertPayload,
    WeeklyTemplateRowUpdate,
    WeeklyTemplateGeneratePayload,
)
from schedule.models import Schedule
from shift.models import Shift

# Timezone is set to iceland for now

# ---------- Queries ----------

def get_weekly_template_row(db: Session, row_id: int) -> WeeklyTemplate | None:
    return db.get(WeeklyTemplate, row_id)

def get_weekly_template_rows(
    db: Session,
    *,
    schedule_id: Optional[int] = None,
    org_id: Optional[int] = None,
    weekday: Optional[int] = None,
    location_id: Optional[int] = None,
    role_id: Optional[int] = None,
) -> list[WeeklyTemplate]:
    stmt = select(WeeklyTemplate)
    if schedule_id is not None:
        stmt = stmt.where(WeeklyTemplate.schedule_id == schedule_id)
    if org_id is not None:
        stmt = stmt.where(WeeklyTemplate.org_id == org_id)
    if weekday is not None:
        stmt = stmt.where(WeeklyTemplate.weekday == weekday)
    if location_id is not None:
        stmt = stmt.where(WeeklyTemplate.location_id == location_id)
    if role_id is not None:
        stmt = stmt.where(WeeklyTemplate.role_id == role_id)
    stmt = stmt.order_by(WeeklyTemplate.weekday, WeeklyTemplate.start_time, WeeklyTemplate.id)
    return list(db.scalars(stmt))


# ---------- Replace-all upsert (Save weekly template) ----------

def upsert_weekly_template(
    db: Session,
    *,
    schedule_id: int,
    payload: WeeklyTemplateUpsertPayload,
) -> list[WeeklyTemplate]:
    sched = db.get(Schedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Delete current rows for this schedule 
    db.execute(delete(WeeklyTemplate).where(WeeklyTemplate.schedule_id == schedule_id))

    rows: list[WeeklyTemplate] = []
    for it in payload.items:
        if it.start_time == it.end_time:
            raise HTTPException(status_code=422, detail="start time and end time cannot be equal")

        row = WeeklyTemplate(
            org_id=sched.org_id,
            schedule_id=schedule_id,
            weekday=it.weekday,
            location_id=it.location_id,
            role_id=it.role_id,
            start_time=it.start_time,
            end_time=it.end_time,
            required_staff_count=it.required_staff_count,
            notes=it.notes,
        )
        rows.append(row)

    db.add_all(rows)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Weekly template contains duplicate slots")

    for r in rows:
        db.refresh(r)
    return rows


# ---------- PATCH a single row ----------

def update_weekly_template_row(
    db: Session,
    *,
    schedule_id: int,
    row_id: int,
    patch: WeeklyTemplateRowUpdate,
) -> WeeklyTemplate | None:
    row = db.get(WeeklyTemplate, row_id)
    if not row or row.schedule_id != schedule_id:
        return None

    data = patch.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)

    # Basic guards
    if row.start_time == row.end_time:
        raise HTTPException(status_code=422, detail="start time and end time cannot be equal")
    if not (0 <= row.weekday <= 6):
        raise HTTPException(status_code=422, detail="weekday must be between 0 and 6")

    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another template row already occupies this slot")
    return row


def delete_weekly_template_row(db: Session, *, schedule_id: int, row_id: int) -> bool:
    row = db.get(WeeklyTemplate, row_id)
    if not row or row.schedule_id != schedule_id:
        return False
    db.delete(row)
    db.commit()
    return True


# ---------- Generate Shifts from Weekly Template ----------

def _combine_local_utc(d: date, t: time) -> datetime:
    """
    Iceland-only: local Reykjavik time == UTC. Return tz-aware UTC datetime.
    """
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)

def _daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    one = timedelta(days=1)
    while cur <= end:
        yield cur
        cur += one

def _delete_shifts_in_range(db: Session, schedule_id: int, start_utc: datetime, end_utc: datetime) -> int:
    res = db.execute(
        delete(Shift).where(
            and_(
                Shift.schedule_id == schedule_id,
                Shift.start_at <= end_utc,
                Shift.end_at >= start_utc,
            )
        )
    )
    return res.rowcount or 0

def _overlaps_clause(
    schedule_id: int,
    location_id: Optional[int],
    role_id: Optional[int],
    start_utc: datetime,
    end_utc: datetime,
):
    conds = [Shift.schedule_id == schedule_id]
    if location_id is not None:
        conds.append(Shift.location_id == location_id)
    if role_id is not None:
        conds.append(Shift.role_id == role_id)
    # time overlap (including exact match)
    conds.append(
        or_(
            and_(Shift.start_at < end_utc, Shift.end_at > start_utc),
            and_(Shift.start_at == start_utc, Shift.end_at == end_utc),
        )
    )
    return and_(*conds)

def generate_from_weekly_template(
    db: Session,
    *,
    schedule_id: int,
    body: WeeklyTemplateGeneratePayload,
) -> dict:
    sched = db.get(Schedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    items = list(db.scalars(
        select(WeeklyTemplate).where(WeeklyTemplate.schedule_id == schedule_id)
    ))
    if not items:
        return {"created": 0, "replaced": 0, "skipped": 0}

    start_local_midnight = _combine_local_utc(body.start_date, time(0, 0, 0))
    end_local_23_59_59   = _combine_local_utc(body.end_date,   time(23, 59, 59))
    window_start_utc = start_local_midnight
    window_end_utc   = end_local_23_59_59

    replaced = 0
    created = 0
    skipped = 0
    to_insert: list[Shift] = []

    try:
        # If replacing, stage the delete first (same transaction)
        if body.policy == "replace":
            replaced = _delete_shifts_in_range(db, schedule_id, window_start_utc, window_end_utc)

        for day in _daterange(body.start_date, body.end_date):
            todays = (it for it in items if it.weekday == day.weekday())
            for it in todays:
                start_utc = _combine_local_utc(day, it.start_time)
                end_utc   = _combine_local_utc(day, it.end_time)
                if end_utc <= start_utc:
                    end_utc += timedelta(days=1)  # overnight

                if body.policy == "fill_missing":
                    exists = db.scalar(
                        select(func.count(Shift.id)).where(
                            _overlaps_clause(schedule_id, it.location_id, it.role_id, start_utc, end_utc)
                        )
                    )
                    if exists and exists > 0:
                        skipped += 1
                        continue

                to_insert.append(Shift(
                    org_id=sched.org_id,
                    schedule_id=schedule_id,
                    location_id=it.location_id,
                    role_id=it.role_id,
                    start_at=start_utc,
                    end_at=end_utc,
                    notes=it.notes,
                    required_staff_count=it.required_staff_count,
                ))
                created += 1

        if to_insert:
            db.add_all(to_insert)

        db.commit()
        return {"created": created, "replaced": replaced, "skipped": skipped}

    except Exception:
        db.rollback()
        raise

