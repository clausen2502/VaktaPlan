from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import OrganizationSchema, OrganizationCreatePayload, OrganizationCreate, OrganizationUpdate
from . import service

organization_router = APIRouter(prefix="/organizations", tags=["organizations"])

@organization_router.get("/me", response_model=OrganizationSchema)
def my_organization(
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    ):
    obj = service.get_organization(db, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="organization not found")
    return obj

@organization_router.get("", response_model=list[OrganizationSchema])
def list_organizations(
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user)
    ):
    return service.list_organizations(db)

# Get org by id
@organization_router.get("/{org_id}", response_model=OrganizationSchema)
def organization_detail(
    org_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_active_user)
    ):
    obj = service.get_organization(db, org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="organization not found")
    return obj

# Create org
@organization_router.post("", response_model=OrganizationSchema, status_code=status.HTTP_201_CREATED)
def organization_post(
    payload: OrganizationCreatePayload,
    db: Session = Depends(get_db),
    _mgr = Depends(require_manager)
    ):
    dto = OrganizationCreate(name=payload.name, timezone=payload.timezone or "Atlantic/Reykjavik")
    try:
        return service.create_organization(db, dto)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="organization name already exists")

# Update org
@organization_router.patch("/{org_id}", response_model=OrganizationSchema)
def organization_patch(
    payload: OrganizationUpdate,
    org_id: int,
    user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _mgr = Depends(require_manager),
    ):
    if user.org_id != org_id:
        raise HTTPException(status_code=403, detail="forbidden: cannot update another organization")
    try:
        return service.update_organization(db, user.org_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="organization name already exists")

# Delete org
@organization_router.delete("/{org_id}")
def organization_delete(
    org_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    # Only allow deleting your own org
    if user.org_id != org_id:
        raise HTTPException(status_code=403, detail="forbidden: cannot delete another organization")

    obj = service.get_organization(db, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="organization not found")

    service.delete_organization(db, user.org_id)
    return {"message": "organization deleted"}

@organization_router.delete("/me")
def organization_delete_me(
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    obj = service.get_organization(db, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="organization not found")
    service.delete_organization(db, user.org_id)
    return {"message": "organization deleted"}
