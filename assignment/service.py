from __future__ import annotations
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assignment
from .schema import AssignmentCreate, AssignmentUpdate
from shift.models import Shift
from employee.models import Employee


# LIST (org-scoped)
def get_assignments(
    db: Session,
    *,
    org_id: int,
    shift_id: Optional[int] = None,
    employee_id: Optional[int] = None,
) -> List[Assignment]:
    stmt = (
        select(Assignment)
        .join(Shift, Shift.id == Assignment.shift_id)
        .join(Employee, Employee.id == Assignment.employee_id)
        .where(Shift.org_id == org_id, Employee.org_id == org_id)
    )
    if shift_id is not None:
        stmt = stmt.where(Assignment.shift_id == shift_id)
    if employee_id is not None:
        stmt = stmt.where(Assignment.employee_id == employee_id)

    stmt = stmt.order_by(Assignment.shift_id, Assignment.employee_id)
    return list(db.scalars(stmt))


# Single (org-scoped)
def get_assignment_for_org(db: Session, shift_id: int, employee_id: int, org_id: int) -> Assignment | None:
    stmt = (
        select(Assignment)
        .join(Shift, Shift.id == Assignment.shift_id)
        .join(Employee, Employee.id == Assignment.employee_id)
        .where(
            Assignment.shift_id == shift_id,
            Assignment.employee_id == employee_id,
            Shift.org_id == org_id,
            Employee.org_id == org_id,
        )
    )
    return db.scalars(stmt).first()


def create_assignment(db: Session, dto: AssignmentCreate) -> Assignment:
    # Validate both ends belong to this org
    shift = db.get(Shift, dto.shift_id)
    if not shift or shift.org_id != dto.org_id:
        raise HTTPException(status_code=404, detail="shift not found")

    emp = db.get(Employee, dto.employee_id)
    if not emp or emp.org_id != dto.org_id:
        raise HTTPException(status_code=404, detail="employee not found")

    row = Assignment(
        shift_id=dto.shift_id,
        employee_id=dto.employee_id,
    )
    db.add(row)
    # Let IntegrityError bubble; router maps to 409 on duplicate composite key
    db.commit()
    db.refresh(row)
    return row


def update_assignment(
    db: Session,
    shift_id: int,
    employee_id: int,
    patch: AssignmentUpdate,
    *,
    org_id: int,
) -> Assignment:
    row = get_assignment_for_org(db, shift_id, employee_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="assignment not found")

    data = patch.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return row


def delete_assignment(db: Session, shift_id: int, employee_id: int) -> None:
    row = db.query(Assignment).filter(
        Assignment.shift_id == shift_id,
        Assignment.employee_id == employee_id
    ).first()
    if row:
        db.delete(row)
        db.commit()
    return
