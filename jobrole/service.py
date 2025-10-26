from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from .models import JobRole
from .schemas import JobRoleCreate, JobRoleUpdate

def get_jobroles(db: Session, *, org_id: int) -> List[JobRole]:
    stmt = select(JobRole).where(JobRole.org_id == org_id).order_by(JobRole.name.asc())
    return list(db.scalars(stmt))

def get_jobrole(db: Session, jobrole_id: int) -> Optional[JobRole]:
    return db.get(JobRole, jobrole_id)

def get_jobrole_for_org(db: Session, jobrole_id: int, org_id: int) -> Optional[JobRole]:
    stmt = select(JobRole).where(JobRole.id == jobrole_id, JobRole.org_id == org_id)
    return db.scalars(stmt).first()

def create_jobrole(db: Session, loc: JobRoleCreate) -> JobRole:
    db_role = JobRole(org_id=loc.org_id, name=loc.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_jobrole(db: Session, jobrole_id: int, patch: JobRoleUpdate) -> JobRole:
    db_role = db.get(JobRole, jobrole_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="jobrole not found")
    data = patch.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in data.items():
        setattr(db_role, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="job role already exists in this organization")
    db.refresh(db_role)
    return db_role

def delete_jobrole(db: Session, jobrole_id: int) -> None:
    db_role = db.get(JobRole, jobrole_id)
    if db_role:
        db.delete(db_role)
        db.commit()
    return
