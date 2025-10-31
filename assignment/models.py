from __future__ import annotations
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class Assignment(Base):
    __tablename__ = "assignments"
    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    shift = relationship("Shift", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments")
