from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from .schemas import ShiftSchema, ShiftCreatePayload, ShiftCreate, ShiftUpdate
from shift import service

shift_router = APIRouter(prefix="/shifts", tags=["Shifts"])

@shift_router.get("", response_model=list[ShiftSchema])
def list_shifts(
    schedule_id: Optional[int] = Query(None, description="Filter by schedule"),
    location_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    return service.get_shifts(
        db,
        org_id=user.org_id,
        schedule_id=schedule_id,
        location_id=location_id,
        start=start,
        end=end,
        notes=notes,
    )

@shift_router.get("/{shift_id}", response_model=ShiftSchema)
def get_shift(shift_id: int, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    obj = service.get_shift_for_org(db, shift_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Shift not found")
    return obj

@shift_router.post("", response_model=ShiftSchema, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreatePayload, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    internal = ShiftCreate(org_id=user.org_id, **payload.model_dump())
    return service.create_shift(db, internal)

@shift_router.patch("/{shift_id}", response_model=ShiftSchema)
def patch_shift(shift_id: int, payload: ShiftUpdate, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    if not service.get_shift_for_org(db, shift_id, user.org_id):
        raise HTTPException(status_code=404, detail="Shift not found")
    return service.update_shift(db, shift_id, payload)

@shift_router.delete("/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db), user = Depends(get_current_active_user)):
    if not service.get_shift_for_org(db, shift_id, user.org_id):
        raise HTTPException(status_code=404, detail="Shift not found")
    service.delete_shift(db, shift_id)
    return {"message": "Shift deleted"}
