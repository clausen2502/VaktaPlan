from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from core.database import Base

class JobRole(Base):
    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    weekly_hours_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)


    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_jobrole_org_name"),
    )

    #relationship
    org = relationship("Organization", back_populates="jobroles")

