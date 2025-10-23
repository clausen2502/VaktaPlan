# location/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import get_db
from .schemas import LocationCreateIn, LocationUpdateIn, LocationRead
from . import service
from authz.deps import require_member, require_manager

# =========================
# READ: employees + managers
# =========================
location_read_router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    dependencies=[Depends(require_member)],
    )

@location_read_router.get("/org/{org_id}", response_model=List[LocationRead])
def get_locations_by_org(
    org_id: int,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_member),
    ):
    if org_id != caller_org_id:
        raise HTTPException(status_code=404, detail="Organization not found")
    return service.get_locations(db, org_id=org_id)

@location_read_router.get("", response_model=List[LocationRead])
def get_locations(
    org_id: Optional[int] = None,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_member),
    ):
    oid = org_id if org_id is not None else caller_org_id
    if oid != caller_org_id:
        raise HTTPException(status_code=404, detail="Organization not found")
    return service.get_locations(db, org_id=oid)

@location_read_router.get("/{location_id}", response_model=LocationRead)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_member),
    ):
    loc = service.get_location_for_org(db, location_id, caller_org_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


# =================
# WRITE: managers only
# =================
location_write_router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    dependencies=[Depends(require_manager)],
    )

@location_write_router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreateIn,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_manager),
    ):
    if getattr(payload, "org_id", caller_org_id) != caller_org_id:
        raise HTTPException(status_code=403, detail="Cannot create location for another organization")
    try:
        fixed = LocationCreateIn(org_id=caller_org_id, name=payload.name)
        return service.create_location(db, fixed)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Location name already exists in this organization")

@location_write_router.patch("/{location_id}", response_model=LocationRead)
def update_location(
    location_id: int,
    payload: LocationUpdateIn,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_manager),
    ):
    if not service.get_location_for_org(db, location_id, caller_org_id):
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        updated = service.update_location(db, location_id, payload)
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Location name already exists in this organization")

@location_write_router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    caller_org_id: int = Depends(require_manager),
    ):
    if not service.get_location_for_org(db, location_id, caller_org_id):
        raise HTTPException(status_code=404, detail="Location not found")
    if not service.delete_location(db, location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    return None
