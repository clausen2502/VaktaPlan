from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Location
from .schemas import LocationCreate, LocationUpdate

def get_locations(db: Session, *, org_id: int) -> List[Location]:
    stmt = select(Location).where(Location.org_id == org_id).order_by(Location.name.asc())
    return list(db.scalars(stmt))

def get_location(db: Session, location_id: int) -> Optional[Location]:
    return db.get(Location, location_id)

def get_location_for_org(db: Session, location_id: int, org_id: int) -> Optional[Location]:
    stmt = select(Location).where(Location.id == location_id, Location.org_id == org_id)
    return db.scalars(stmt).first()

def create_location(db: Session, loc: LocationCreate) -> Location:
    db_loc = Location(org_id=loc.org_id, name=loc.name)
    db.add(db_loc)
    db.commit()
    db.refresh(db_loc)
    return db_loc

def update_location(db: Session, location_id: int, patch: LocationUpdate) -> Optional[Location]:
    db_loc = db.get(Location, location_id)
    if not db_loc:
        return None
    data = patch.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_loc, k, v)
    db.commit(); db.refresh(db_loc)
    return db_loc

def delete_location(db: Session, location_id: int) -> None:
    db_loc = db.get(Location, location_id)
    if db_loc:
        db.delete(db_loc); db.commit()
    return
