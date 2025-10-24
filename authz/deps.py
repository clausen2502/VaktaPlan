from fastapi import Depends, HTTPException
from auth.services.auth_service import get_current_active_user
from user.models import User

def require_member(user: User = Depends(get_current_active_user)) -> int:
    return user.org_id

def require_manager(user: User = Depends(get_current_active_user)) -> int:
    if not user.is_manager:
        raise HTTPException(status_code=403, detail="Manager role required")
