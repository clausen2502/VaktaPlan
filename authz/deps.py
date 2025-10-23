# authz/deps.py
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from user.models import User

def require_member(
    user: User = Depends(get_current_active_user),
    ) -> int:
    #  assume user has a single org_id on the user row
    if getattr(user, "org_id", None) is None:
        raise HTTPException(status_code=403, detail="User is not assigned to any organization")
    return user.org_id

def require_manager(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    ) -> int:

    if not getattr(user, "is_manager", False):
        raise HTTPException(status_code=403, detail="Managers only")
    if getattr(user, "org_id", None) is None:
        raise HTTPException(status_code=403, detail="User is not assigned to any organization")
    return user.org_id
