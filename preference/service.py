# preference/service.py
from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .models import Preference
from .schema import PreferenceCreate, PreferenceUpdate
from employee.models import Employee


def get_preference(db: Session, pref_id: int) -> Preference | None:
    return db.query(Preference).filter(Preference.id == pref_id).first()


def get_preference_for_org(db: Session, pref_id: int, org_id: int) -> Preference | None:
    """
    Fetch a single preference 
    """
    statement = (
        select(Preference)
        .join(Employee, Employee.id == Preference.employee_id)
        .where(Preference.id == pref_id, Employee.org_id == org_id)
    )
    return db.scalars(statement).first()


def get_preferences(
    db: Session,
    *,
    org_id: int,
    employee_id: Optional[int] = None,
    weekday: Optional[int] = None,
    role_id: Optional[int] = None,
    location_id: Optional[int] = None,
    active_on: Optional[date] = None,
    ) -> list[Preference]:
    """
    List preferences scoped to org, with optional filters.
    """
    statement = (
        select(Preference)
        .join(Employee, Employee.id == Preference.employee_id)
        .where(Employee.org_id == org_id)
    )
    if employee_id is not None:
        statement = statement.where(Preference.employee_id == employee_id)
    if weekday is not None:
        statement = statement.where(Preference.weekday == weekday)
    if role_id is not None:
        statement = statement.where(Preference.role_id == role_id)
    if location_id is not None:
        statement = statement.where(Preference.location_id == location_id)
    if active_on is not None:
        statement = statement.where(
            and_(
                or_(Preference.active_start.is_(None), Preference.active_start <= active_on),
                or_(Preference.active_end.is_(None), Preference.active_end >= active_on),
            )
        )

    statement = statement.order_by(
        Preference.employee_id,
        Preference.weekday.is_(None),
        Preference.weekday,
        Preference.start_time.is_(None),
        Preference.start_time,
    )
    return list(db.scalars(statement))


def _ensure_employee_in_org(db: Session, employee_id: int, org_id: int) -> None:
    ok = db.scalar(
        select(Employee.id).where(Employee.id == employee_id, Employee.org_id == org_id)
    )
    if not ok:
        # Either employee doesn’t exist or belongs to another org
        raise HTTPException(status_code=403, detail="Cross-organization access forbidden")


def create_preference(db: Session, pref: PreferenceCreate) -> Preference:
    _ensure_employee_in_org(db, pref.employee_id, pref.org_id)

    db_pref = Preference(
        employee_id=pref.employee_id,
        weekday=pref.weekday,
        start_time=pref.start_time,
        end_time=pref.end_time,
        role_id=pref.role_id,
        location_id=pref.location_id,
        weight=pref.weight,
        do_not_schedule=pref.do_not_schedule,
        notes=pref.notes,
        active_start=pref.active_start,
        active_end=pref.active_end,
    )
    db.add(db_pref)
    db.commit()
    db.refresh(db_pref)
    return db_pref


def update_preference(db: Session, pref_id: int, patch: PreferenceUpdate, org_id: int) -> Preference:
    # Ensure the preference belongs to this org
    db_pref = get_preference_for_org(db, pref_id, org_id)
    if not db_pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    data = patch.model_dump(exclude_unset=True, exclude_none=True)

    # Merge-level validation for time pair
    new_start_time = data.get("start_time", db_pref.start_time)
    new_end_time = data.get("end_time", db_pref.end_time)
    if new_start_time is not None and new_end_time is not None:
        if new_start_time >= new_end_time:
            raise HTTPException(status_code=422, detail="start time must be before end time")

    # Merge-level validation for active window
    new_active_start = data.get("active_start", db_pref.active_start)
    new_active_end = data.get("active_end", db_pref.active_end)
    if new_active_start is not None and new_active_end is not None:
        if new_active_start > new_active_end:
            raise HTTPException(status_code=422, detail="start must be on or before end")

    for k, v in data.items():
        setattr(db_pref, k, v)

    db.commit()
    db.refresh(db_pref)
    return db_pref


def delete_preference(db: Session, pref_id: int) -> None:
    db_pref = db.query(Preference).filter(Preference.id == pref_id).first()
    if db_pref:
        db.delete(db_pref)
        db.commit()
    return
