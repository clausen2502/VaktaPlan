from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from .schemas import ShiftRead
from . import service

shift_router = APIRouter(prefix="/shifts", tags=["shifts"])

@shift_router.get("/", response_model=list[ShiftRead])
def get_shifts(db: Session = Depends(get_db)):
    return service.list_shifts(db)
