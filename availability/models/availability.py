from __future__ import annotations
from datetime import time
from sqlalchemy import ForeignKey, Time, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )

    # 0=Monday .. 6=Sunday
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)

    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time:   Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "weekday", "start_time", "end_time",
            name="unique_availability_slot"
        ),
    )
