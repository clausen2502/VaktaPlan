from enum import Enum
from sqlalchemy import ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class MemberRole(str, Enum):
    manager = "manager"
    employee = "employee"

class OrgMember(Base):
    __tablename__ = "org_members"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # common filter: WHERE org_id=...
    )
    role: Mapped[MemberRole] = mapped_column(
        SAEnum(MemberRole, name="member_role"),
        nullable=False,
        index=True,
    )

    # relationships
    org = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")
