from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import PublicationSchema, PublicationCreatePayload, PublicationCreate
from . import service

publication_router = APIRouter(prefix="/publications", tags=["Publications"])

# List (scoped to caller's org)
@publication_router.get("", response_model=list[PublicationSchema])
def list_publications(
    active_on: Optional[date] = Query(None, description="Return publications covering this date"),
    start_from: Optional[date] = Query(None, description="range_start >= start_from"),
    end_to: Optional[date] = Query(None, description="range_end <= end_to"),
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    return service.get_publications(
        db,
        org_id=user.org_id,
        active_on=active_on,
        start_from=start_from,
        end_to=end_to,
    )

# Get by id (scoped)
@publication_router.get("/{publication_id}", response_model=PublicationSchema)
def get_publication(
    publication_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
):
    obj = service.get_publication_for_org(db, publication_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="publication not found")
    return obj

# Create (manager only)
@publication_router.post("", response_model=PublicationSchema, status_code=status.HTTP_201_CREATED)
def create_publication(
    payload: PublicationCreatePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    dto = PublicationCreate(
        org_id=user.org_id,
        user_id=user.id,  # who publishes
        range_start=payload.range_start,
        range_end=payload.range_end,
        version=payload.version,
    )
    try:
        return service.create_publication(db, dto)
    except IntegrityError:
        db.rollback()
        # If you later add a UNIQUE(org_id, range_start, range_end, version)
        # this maps cleanly to 409:
        raise HTTPException(status_code=409, detail="publication already exists for this range and version")

# Delete (manager only)
@publication_router.delete("/{publication_id}")
def delete_publication(
    publication_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
):
    obj = service.get_publication_for_org(db, publication_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="publication not found")
    service.delete_publication(db, publication_id)
    return {"message": "publication deleted"}
