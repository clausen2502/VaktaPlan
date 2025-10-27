from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import ScheduleSchema, ScheduleCreatePayload, ScheduleCreate
from . import service 

schedule_router = APIRouter(prefix="/schedules", tags=["Schedules"])

# List (scoped to caller's org)
@schedule_router.get("", response_model=list[ScheduleSchema])
def list_schedules(
    active_on: Optional[date] = Query(None, description="Return schedules covering this date"),
    start_from: Optional[date] = Query(None, description="range_start >= start_from"),
    end_to: Optional[date] = Query(None, description="range_end <= end_to"),
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    return service.get_schedules(
        db,
        org_id=user.org_id,
        active_on=active_on,
        start_from=start_from,
        end_to=end_to,
    )

# Get by id (scoped)
@schedule_router.get("/{schedule_id}", response_model=ScheduleSchema)
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    obj = service.get_schedule_for_org(db, schedule_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="schedule not found")
    return obj

# Create (manager only)
@schedule_router.post("", response_model=ScheduleSchema, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreatePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    dto = ScheduleCreate(
        org_id=user.org_id,
        created_by=user.id,  # who created the schedule
        range_start=payload.range_start,
        range_end=payload.range_end,
        version=payload.version,
    )
    try:
        return service.create_schedule(db, dto)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="schedule already exists for this range and version",
        )

# Delete (manager only)
@schedule_router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    obj = service.get_schedule_for_org(db, schedule_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="schedule not found")
    service.delete_schedule(db, schedule_id)
    return {"message": "schedule deleted"}
