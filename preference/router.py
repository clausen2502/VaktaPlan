# preference/router.py
from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import PreferenceSchema, PreferenceCreatePayload, PreferenceCreate, PreferenceUpdate
from . import service

pref_router = APIRouter(prefix="/preferences", tags=["Preferences"])

# Get all preferences (scoped to caller org) with optional filters
@pref_router.get("", response_model=list[PreferenceSchema])
def list_preferences(
    employee_id: Optional[int] = None,
    weekday: Optional[int] = Query(None, description="0=Mon .. 6=Sun"),
    role_id: Optional[int] = None,
    location_id: Optional[int] = None,
    active_on: Optional[date] = Query(None, description="Filter by date within active window"),
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    return service.get_preferences(
        db,
        org_id=user.org_id,
        employee_id=employee_id,
        weekday=weekday,
        role_id=role_id,
        location_id=location_id,
        active_on=active_on,
    )

# Get a preference by id (scoped)
@pref_router.get("/{preference_id}", response_model=PreferenceSchema)
def get_preference(
    preference_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    obj = service.get_preference_for_org(db, preference_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="preference not found")
    return obj

# Create a preference (manager only)
@pref_router.post("", response_model=PreferenceSchema, status_code=status.HTTP_201_CREATED)
def create_preference(
    payload: PreferenceCreatePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    internal = PreferenceCreate(org_id=user.org_id, **payload.model_dump())
    try:
        return service.create_preference(db, internal)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="preference already exists for these fields")

# Update a preference (manager only)
@pref_router.patch("/{preference_id}", response_model=PreferenceSchema)
def update_preference(
    preference_id: int,
    payload: PreferenceUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    if not service.get_preference_for_org(db, preference_id, user.org_id):
        raise HTTPException(status_code=404, detail="preference not found")
    return service.update_preference(db, preference_id, payload, org_id=user.org_id)

# Delete a preference (manager only)
@pref_router.delete("/{preference_id}")
def delete_preference(
    preference_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    if not service.get_preference_for_org(db, preference_id, user.org_id):
        raise HTTPException(status_code=404, detail="preference not found")
    service.delete_preference(db, preference_id)
    return {"message": "preference deleted"}
