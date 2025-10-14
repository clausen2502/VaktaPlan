from sqlalchemy.orm import Session
from .models import Shift

def list_shifts(db: Session):
    return db.query(Shift).order_by(Shift.start_at).all()
