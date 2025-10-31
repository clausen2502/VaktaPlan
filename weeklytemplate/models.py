from __future__ import annotations
from datetime import time
from sqlalchemy import Integer, Time, Text, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class WeeklyTemplate(Base):
    __tablename__ = "weekly_template_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), index=True)

    weekday: Mapped[int] = mapped_column(Integer, nullable=False)

    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), index=True, nullable=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("job_roles.id", ondelete="SET NULL"), index=True, nullable=True)

    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time:   Mapped[time] = mapped_column(Time, nullable=False)

    required_staff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # relationships
    schedule = relationship("Schedule", back_populates="weeklytemplate")
    location = relationship("Location", lazy="joined", passive_deletes=True)
    role = relationship("JobRole")
    org = relationship("Organization")

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_weeklytpl_weekday"),
        CheckConstraint("start_time <> end_time", name="ck_weeklytpl_nonzero"),
        UniqueConstraint(
            "schedule_id", "weekday", "location_id", "role_id", "start_time", "end_time",
            name="uq_weeklytpl_slot"
        ),
        Index("ix_weeklytpl_sched_weekday", "schedule_id", "weekday"),
    )
