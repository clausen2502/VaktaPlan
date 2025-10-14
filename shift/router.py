from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from .schemas import ShiftRead
from .service import list_shifts

shift_router = APIRouter(prefix="/shifts", tags=["Shifts"])

@shift_router.get("/", response_model=list[ShiftRead])
def get_shifts(
    org_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    ):
    return list_shifts(db, org_id=org_id, start=start, end=end)