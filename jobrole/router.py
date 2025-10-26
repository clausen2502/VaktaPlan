from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager
from .schemas import JobRoleSchema, JobRoleCreatePayload, JobRoleCreate, JobRoleUpdate
from . import service

jobrole_router = APIRouter(prefix="/jobroles", tags=["jobroles"])

# List all jobroles
@jobrole_router.get("", response_model=list[JobRoleSchema])
def list_jobroles(db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    return service.get_jobroles(db, org_id=user.org_id)

# Get jobrole by id
@jobrole_router.get("/{jobrole_id}", response_model=JobRoleSchema)
def jobrole_detail(jobrole_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_jobrole_for_org(db, jobrole_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="jobrole not found")
    return obj

# Create jobrole
@jobrole_router.post("", response_model=JobRoleSchema, status_code=status.HTTP_201_CREATED)
def jobrole_post(payload: JobRoleCreatePayload, db: Session = Depends(get_db), user=Depends(get_current_active_user), _mgr = Depends(require_manager)):
    internal = JobRoleCreate(org_id=user.org_id, name=payload.name)
    try:
        return service.create_jobrole(db, internal)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="jobrole name already exists in this organization")

# Update jobrole
@jobrole_router.patch("/{jobrole_id}", response_model=JobRoleSchema)
def jobrole_patch(jobrole_id: int, payload: JobRoleUpdate, db: Session = Depends(get_db), user=Depends(get_current_active_user), _mgr = Depends(require_manager)):
    obj = service.get_jobrole_for_org(db, jobrole_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="jobrole not found")
    return service.update_jobrole(db, jobrole_id, payload)

# Delete jobrole
@jobrole_router.delete("/{jobrole_id}")
def jobrole_delete(jobrole_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user), _mgr = Depends(require_manager)):
    obj = service.get_jobrole_for_org(db, jobrole_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="jobrole not found")
    service.delete_jobrole(db, jobrole_id)
    return {"message": "jobrole deleted"}
