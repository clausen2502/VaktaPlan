from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, ForeignKey, Index, UniqueConstraint
from core.database import Base

class Unavailability(Base):
    __tablename__ = "unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason:   Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (
        Index("ix_unavail_emp_start", "employee_id", "start_at"),
        UniqueConstraint("employee_id", "start_at", "end_at", name="unique_unavailable_exact"),
    )
