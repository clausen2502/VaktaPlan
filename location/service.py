from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Location
from .schemas import LocationCreateIn, LocationUpdateIn

def get_locations(db: Session, org_id: Optional[int] = None) -> List[Location]:
    statement = select(Location).order_by(Location.name.asc())
    if org_id is not None:
        statement = statement.where(Location.org_id == org_id)
    return list(db.scalars(statement))

def get_location(db: Session, location_id: int) -> Optional[Location]:
    return db.get(Location, location_id)

# Safer helper: fetch by id + org
def get_location_for_org(db: Session, location_id: int, org_id: int) -> Optional[Location]:
    statement = select(Location).where(Location.id == location_id, Location.org_id == org_id)
    return db.scalars(statement).first()

def create_location(db: Session, payload: LocationCreateIn) -> Location:
    location = Location(org_id=payload.org_id, name=payload.name)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location

def update_location(db: Session, location_id: int, payload: LocationUpdateIn) -> Optional[Location]:
    location = db.get(Location, location_id)
    if not location:
        return None
    data = payload.model_dump(exclude_unset=True)
    data.pop("org_id", None)  # org_id immutable
    for k, v in data.items():
        setattr(location, k, v)
    db.commit()
    db.refresh(location)
    return location

def delete_location(db: Session, location_id: int) -> bool:
    location = db.get(Location, location_id)
    if not location:
        return False
    db.delete(location)
    db.commit()
    return True
