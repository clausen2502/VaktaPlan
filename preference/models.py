from __future__ import annotations
from datetime import time, date
from sqlalchemy import ForeignKey, Time, Integer, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    
    weekday: Mapped[int | None] = mapped_column(nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time:   Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    active_start: Mapped[date | None] = mapped_column(nullable=True)
    active_end:   Mapped[date | None] = mapped_column(nullable=True)

    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)

    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g., 0..5
    do_not_schedule: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "weekday", "start_time", "end_time",
            "do_not_schedule", "role_id", "location_id",
            name="uq_preference_full"
        ),
    )
