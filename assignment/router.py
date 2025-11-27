from __future__ import annotations
from typing import Optional, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import (
    AssignmentSchema,
    AssignmentCreatePayload,
    AssignmentCreate,
    AssignmentUpdate,
    AutoAssignRequest,
    AutoAssignResponse,
    )
from . import service
from schedule.models import Schedule
from .auto_assign_service import auto_assign as auto_assign_service


assignment_router = APIRouter(prefix="/assignments", tags=["Assignments"])

# List assignments (scoped to caller's org). Optional filters.
@assignment_router.get("", response_model=list[AssignmentSchema])
def list_assignments(
    shift_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    return service.get_assignments(
        db,
        org_id=user.org_id,
        shift_id=shift_id,
        employee_id=employee_id,
    )

# Get single assignment by composite id (scoped)
@assignment_router.get("/{shift_id}/{employee_id}", response_model=AssignmentSchema)
def get_assignment(
    shift_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    obj = service.get_assignment_for_org(db, shift_id, employee_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="assignment not found")
    return obj

# Create assignment (manager only)
@assignment_router.post("", response_model=AssignmentSchema, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreatePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    dto = AssignmentCreate(org_id=user.org_id, **payload.model_dump())
    try:
        return service.create_assignment(db, dto)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="assignment already exists for this shift/employee")

# Update assignment (manager only)
@assignment_router.patch("/{shift_id}/{employee_id}", response_model=AssignmentSchema)
def update_assignment(
    shift_id: int,
    employee_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    # 404 pre-check like your other routers
    if not service.get_assignment_for_org(db, shift_id, employee_id, user.org_id):
        raise HTTPException(status_code=404, detail="assignment not found")
    # Only preference_score is updatable
    try:
        return service.update_assignment(db, shift_id, employee_id, payload, org_id=user.org_id)
    except IntegrityError:
        db.rollback()
        # Not super likely on update, but keep consistent
        raise HTTPException(status_code=409, detail="assignment already exists for this shift/employee")

# Delete assignment (manager only)
@assignment_router.delete("/{shift_id}/{employee_id}")
def delete_assignment(
    shift_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    if not service.get_assignment_for_org(db, shift_id, employee_id, user.org_id):
        raise HTTPException(status_code=404, detail="assignment not found")
    service.delete_assignment(db, shift_id, employee_id)
    return {"message": "assignment deleted"}

@assignment_router.post("/auto-assign", response_model=AutoAssignResponse)
def run_auto_assign(
    payload: AutoAssignRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    sched = db.get(Schedule, payload.schedule_id)
    if not sched or sched.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="schedule not found")

    result = auto_assign_service(
        db=db,
        schedule_id=payload.schedule_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        policy=payload.policy,
        dry_run=payload.dry_run,
    )
    return result
