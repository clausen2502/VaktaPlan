from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from .schemas import LocationSchema, LocationCreatePayload, LocationCreate, LocationUpdate
from . import service

location_router = APIRouter(prefix="/locations", tags=["Locations"])

# List all locations
@location_router.get("", response_model=list[LocationSchema])
def list_locations(db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    return service.get_locations(db, org_id=user.org_id)

# Get location by id
@location_router.get("/{location_id}", response_model=LocationSchema)
def location_detail(location_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_location_for_org(db, location_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")
    return obj

# Create location
@location_router.post("", response_model=LocationSchema, status_code=status.HTTP_201_CREATED)
def location_post(payload: LocationCreatePayload, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    internal = LocationCreate(org_id=user.org_id, name=payload.name)
    try:
        return service.create_location(db, internal)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Location name already exists in this organization")

# Update location
@location_router.patch("/{location_id}", response_model=LocationSchema)
def location_patch(location_id: int, payload: LocationUpdate, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_location_for_org(db, location_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")
    return service.update_location(db, location_id, payload)

# Delete location
@location_router.delete("/{location_id}")
def location_delete(location_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_location_for_org(db, location_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")
    service.delete_location(db, location_id)
    return {"message": "Location deleted"}
