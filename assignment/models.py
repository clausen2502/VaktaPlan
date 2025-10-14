from __future__ import annotations
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class Assignment(Base):
    __tablename__ = "assignments"
    # composite PK
    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    preference_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # relationships 
    shift = relationship("Shift")
    employee = relationship("Employee")
