from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from auth.services.auth_service import get_current_active_user
from core.database import get_db
from user.models import User
from authz.deps import require_manager
from user.schemas import UserSchema, UserCreate, ManagerSignup
from user.service import get_users, create_user, get_user, delete_user, signup_manager_with_org

user_router = APIRouter(
    prefix='/users',
    tags=['Users']
)

# Get all users
@user_router.get('/', response_model=list[UserSchema])
def user_list(db: Session = Depends(get_db)):
    db_users = get_users(db)

    return db_users

# Get current user
@user_router.get('/me', response_model=UserSchema)
def user_list(current_user: User = Depends(get_current_active_user)):
    return current_user

# Get user details
@user_router.get('/{user_id}', response_model=UserSchema)
def user_detail(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return db_user

# Delete a user
@user_router.delete('/{user_id}')
def user_delete(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    delete_user(db, db_user.id)
    return {"message": "User deleted"}

# Create a user
@user_router.post("/", response_model=UserSchema)
def user_post(user: UserCreate, db:Session = Depends(get_db)):
    return create_user(db, user)


# Sign up as a manager
@user_router.post("/signup-manager", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def signup_manager(payload: ManagerSignup, db: Session = Depends(get_db)):
    return signup_manager_with_org(db, payload)
