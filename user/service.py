from sqlalchemy.orm import Session

from auth.utils.auth_utils import get_password_hash
from organization.models import Organization
from user.models import User
from user.schemas import UserCreate, ManagerSignup


def get_users(db: Session):
    return db.query(User).all()


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate):
    db_user = User(
        email=str(user.email),
        username=user.username,
        password_hash=get_password_hash(user.password),
        is_admin=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return

def signup_manager_with_org(db: Session, p: ManagerSignup) -> User:
    org = Organization(name=p.org_name, timezone="GMT")
    db.add(org)
    db.flush()

    user = User(
        email=str(p.email),
        username=p.username,
        password_hash=get_password_hash(p.password),
        org_id=org.id,
        is_manager=True,
        is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user