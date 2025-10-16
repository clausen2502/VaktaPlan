# routers/shifts.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from .schemas import ShiftRead, ShiftCreateIn
from .service import list_shifts, create_shift
from .models import ShiftStatus

shift_router = APIRouter(prefix="/shifts", tags=["Shifts"])

# GET /shifts?org_id=...&location_id=...&status=...&start=...&end=...&notes=...
@shift_router.get("/", response_model=list[ShiftRead])
def get_shifts(
    org_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status: Optional[ShiftStatus] = Query(None, description="draft|published"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    objs = list_shifts(
        db,
        org_id=org_id,
        location_id=location_id,
        start=start,
        end=end,
        status=status,
        notes=notes,
    )
    return [ShiftRead.model_validate(o, from_attributes=True) for o in objs]

# POST /shifts
@shift_router.post("", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift_endpoint(
    payload: ShiftCreateIn,
    db: Session = Depends(get_db),
):
    obj = create_shift(db, payload)
    return ShiftRead.model_validate(obj, from_attributes=True)