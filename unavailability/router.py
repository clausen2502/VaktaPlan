from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import UnavailabilitySchema, UnavailabilityCreatePayload, UnavailabilityCreate, UnavailabilityUpdate
from . import service

unavailability_router = APIRouter(prefix="/unavailability", tags=["Unavailability"])

# List all unavailability rows (scoped to caller's org), optional filter by employee_id.
@unavailability_router.get("", response_model=list[UnavailabilitySchema])
def list_unavailability(
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    return service.get_unavailability(
        db,
        org_id=user.org_id,
        employee_id=employee_id,
    )

# Get single row by id (scoped)
@unavailability_router.get("/{unavail_id}", response_model=UnavailabilitySchema)
def get_unavailability(
    unavail_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    obj = service.get_unavailability_for_org(db, unavail_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="unavailability not found")
    return obj

# Create (manager only)
@unavailability_router.post("", response_model=UnavailabilitySchema, status_code=status.HTTP_201_CREATED)
def create_unavailability(
    payload: UnavailabilityCreatePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    dto = UnavailabilityCreate(org_id=user.org_id, **payload.model_dump())
    try:
        return service.create_unavailability(db, dto)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="unavailability already exists for this window")

# Update (manager only)
@unavailability_router.patch("/{unavail_id}", response_model=UnavailabilitySchema)
def update_unavailability(
    unavail_id: int,
    payload: UnavailabilityUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    # Prefetch for 404 like your Preference router does
    if not service.get_unavailability_for_org(db, unavail_id, user.org_id):
        raise HTTPException(status_code=404, detail="unavailability not found")
    try:
        return service.update_unavailability(db, unavail_id, payload, org_id=user.org_id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="unavailability already exists for this window")

# Delete (manager only)
@unavailability_router.delete("/{unavail_id}")
def delete_unavailability(
    unavail_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    if not service.get_unavailability_for_org(db, unavail_id, user.org_id):
        raise HTTPException(status_code=404, detail="unavailability not found")
    service.delete_unavailability(db, unavail_id)
    return {"message": "unavailability deleted"}
