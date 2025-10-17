# shift/router.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from .schemas import ShiftRead, ShiftCreateIn, ShiftUpdateIn
from .models import ShiftStatus
from . import service

shift_router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"]
    )

# GET list
@shift_router.get("/", response_model=list[ShiftRead])
def get_shifts(
    location_id: Optional[int] = None,
    status: Optional[ShiftStatus] = Query(None, description="draft|published"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    objs = service.get_shifts(
        db,
        location_id=location_id,
        status=status,
        start=start,
        end=end,
        notes=notes,
    )
    return objs

# GET by id
@shift_router.get("/{shift_id}", response_model=ShiftRead)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    return service.get_shift(db, shift_id)

# Create
@shift_router.post("", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(payload: ShiftCreateIn, db: Session = Depends(get_db)):
    return service.create_shift(db, payload)

# Delete
@shift_router.delete("/{shift_id}", status_code=status.HTTP_200_OK)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    db_shift = service.get_shift(db, shift_id)
    if db_shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    service.delete_shift(db, shift_id)
    return {"message": "Shift Deleted"}

# Update
@shift_router.patch("/{shift_id}", response_model=ShiftRead, status_code=status.HTTP_200_OK)
def patch_shift(shift_id: int, payload: ShiftUpdateIn, db: Session = Depends(get_db)):
    return service.update_shift(db, shift_id, payload)