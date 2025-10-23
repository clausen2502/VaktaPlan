# shift/router.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from .schemas import ShiftRead, ShiftCreateIn, ShiftUpdateIn
from .models import ShiftStatus
from shift import service
from auth.services.auth_service import get_current_active_user

shift_router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"]
)

# GET list (force to caller's org)
@shift_router.get("/", response_model=list[ShiftRead])
def get_shifts(
    location_id: Optional[int] = None,
    status: Optional[ShiftStatus] = Query(None, description="draft|published"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    objs = service.get_shifts(
        db,
        org_id=user.org_id,
        location_id=location_id,
        status=status,
        start=start,
        end=end,
        notes=notes,
    )
    return objs

# GET by id (404 if not in caller's org)
@shift_router.get("/{shift_id}", response_model=ShiftRead)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),  # <-- add
    ):
    shift = service.get_shift_for_org(db, shift_id, user.org_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift

# Create (reject or override org_id)
@shift_router.post("", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreateIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    if payload.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Cannot create shift for another organization")

    return service.create_shift(db, payload)

# Delete (404 if shift not in caller's org)
@shift_router.delete("/{shift_id}", status_code=status.HTTP_200_OK)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    db_shift = service.get_shift_for_org(db, shift_id, user.org_id)
    if db_shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    service.delete_shift(db, shift_id)
    return {"message": "Shift Deleted"}

# Update (404 if shift not in caller's org; also prevent org_id changes)
@shift_router.patch("/{shift_id}", response_model=ShiftRead, status_code=status.HTTP_200_OK)
def patch_shift(
    shift_id: int,
    payload: ShiftUpdateIn,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    # Guard: ensure target belongs to caller's org
    exists = service.get_shift_for_org(db, shift_id, user.org_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Shift not found")

    data = payload.model_dump(exclude_unset=True)
    if "org_id" in data and data["org_id"] != user.org_id:
        raise HTTPException(status_code=403, detail="Cannot move shift to another organization")

    return service.update_shift(db, shift_id, payload)