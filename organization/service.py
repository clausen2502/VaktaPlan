from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from .models import Organization
from .schema import OrganizationCreate, OrganizationUpdate

def list_organizations(db: Session) -> List[Organization]:
    stmt = select(Organization).order_by(Organization.name.asc())
    return list(db.scalars(stmt))

def get_organization(db: Session, org_id: int) -> Optional[Organization]:
    return db.get(Organization, org_id)

def create_organization(db: Session, dto: OrganizationCreate) -> Organization:
    org = Organization(name=dto.name, timezone=dto.timezone or "Atlantic/Reykjavik")
    db.add(org)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="organization name already exists")
    db.refresh(org)
    return org

def update_organization(db: Session, org_id: int, patch: OrganizationUpdate) -> Organization:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="organization not found")

    data = patch.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(org, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="organization name already exists")

    db.refresh(org)
    return org

def delete_organization(db: Session, org_id: int) -> None:
    org = db.get(Organization, org_id)
    if org:
        db.delete(org)
        db.commit()
    return
