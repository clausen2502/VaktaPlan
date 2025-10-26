from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from .models import Unavailability
from .schema import UnavailabilityCreate, UnavailabilityUpdate
from employee.models import Employee


# -------- helpers --------

def _ensure_employee_in_org(db: Session, employee_id: int, org_id: int) -> None:
    ok = db.scalar(
        select(Employee.id).where(Employee.id == employee_id, Employee.org_id == org_id)
    )
    if not ok:
        raise HTTPException(status_code=403, detail="cross-organization access forbidden")


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _validate_window(start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise HTTPException(status_code=422, detail="start_at must be before end_at")


# -------- queries --------

def get_unavailability(db: Session, ua_id: int) -> Unavailability | None:
    """Fetch by id (no org scoping)."""
    return db.get(Unavailability, ua_id)


def get_unavailability_for_org(db: Session, ua_id: int, org_id: int) -> Unavailability | None:
    """Fetch a single row scoped to an organization via Employee join."""
    stmt = (
        select(Unavailability)
        .join(Employee, Employee.id == Unavailability.employee_id)
        .where(Unavailability.id == ua_id, Employee.org_id == org_id)
    )
    return db.scalars(stmt).first()


def get_unavailabilities(
    db: Session,
    *,
    org_id: int,
    employee_id: Optional[int] = None,
    overlaps_start: Optional[datetime] = None,
    overlaps_end: Optional[datetime] = None,
) -> List[Unavailability]:
    """List rows for an org, with optional employee filter and overlap window."""
    stmt = (
        select(Unavailability)
        .join(Employee, Employee.id == Unavailability.employee_id)
        .where(Employee.org_id == org_id)
    )
    if employee_id is not None:
        stmt = stmt.where(Unavailability.employee_id == employee_id)

    if overlaps_start is not None and overlaps_end is not None:
        s = _aware(overlaps_start)
        e = _aware(overlaps_end)
        # overlap if (start < e) AND (end > s)
        stmt = stmt.where(and_(Unavailability.start_at < e, Unavailability.end_at > s))

    stmt = stmt.order_by(Unavailability.employee_id, Unavailability.start_at.asc())
    return list(db.scalars(stmt))


# -------- mutations --------

def create_unavailability(db: Session, dto: UnavailabilityCreate) -> Unavailability:
    _ensure_employee_in_org(db, dto.employee_id, dto.org_id)

    start = _aware(dto.start_at)
    end = _aware(dto.end_at)
    _validate_window(start, end)

    row = Unavailability(
        employee_id=dto.employee_id,
        start_at=start,
        end_at=end,
        reason=dto.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_unavailability(
    db: Session,
    ua_id: int,
    patch: UnavailabilityUpdate,
    org_id: int ) -> Unavailability | None:
    row = get_unavailability_for_org(db, ua_id, org_id)
    if not row:
        exists_any = get_unavailability(db, ua_id)
        if exists_any:
            # exists but not in this org
            raise HTTPException(status_code=404, detail="unavailability not found")
        # truly missing
        return None

    data = patch.model_dump(exclude_unset=True)
    new_start = _aware(data.get("start_at", row.start_at))
    new_end = _aware(data.get("end_at", row.end_at))
    if new_start is not None and new_end is not None:
        _validate_window(new_start, new_end)

    for k, v in data.items():
        setattr(row, k, _aware(v) if k in ("start_at", "end_at") else v)

    db.commit()
    db.refresh(row)
    return row


def delete_unavailability(db: Session, ua_id: int, *, org_id: int) -> bool:
    row = get_unavailability_for_org(db, ua_id, org_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
