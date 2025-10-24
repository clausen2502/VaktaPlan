# shift/router.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from .schemas import ShiftRead, ShiftCreatePayload, ShiftCreateIn, ShiftUpdateIn
from .models import ShiftStatus
from shift import service

shift_router = APIRouter(prefix="/shifts", tags=["Shifts"])

## Get all shifts
@shift_router.get("", response_model=list[ShiftRead])
def list_shifts(
    location_id: Optional[int] = None,
    status: Optional[ShiftStatus] = Query(None, description="draft|published"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    return service.get_shifts(
        db,
        org_id=user.org_id,
        location_id=location_id,
        status=status,
        start=start,
        end=end,
        notes=notes,
    )

## Get a shift by id
@shift_router.get("/{shift_id}", response_model=ShiftRead)
def get_shift(shift_id: int, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    obj = service.get_shift_for_org(db, shift_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Shift not found")
    return obj

# Create a shift
@shift_router.post("", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreatePayload, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    internal = ShiftCreateIn(org_id=user.org_id, **payload.model_dump())
    return service.create_shift(db, internal)

# Update shift
@shift_router.patch("/{shift_id}", response_model=ShiftRead)
def patch_shift(shift_id: int, payload: ShiftUpdateIn, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    if not service.get_shift_for_org(db, shift_id, user.org_id):
        raise HTTPException(status_code=404, detail="Shift not found")
    return service.update_shift(db, shift_id, payload)

# Delete shift
@shift_router.delete("/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    if not service.get_shift_for_org(db, shift_id, user.org_id):
        raise HTTPException(status_code=404, detail="Shift not found")
    service.delete_shift(db, shift_id)
    return {"message": "Shift Deleted"}
