from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from sqlalchemy import Date, DateTime, Integer, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class ScheduleStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"

class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)

    range_start: Mapped[date] = mapped_column(Date(), nullable=False)
    range_end:   Mapped[date] = mapped_column(Date(), nullable=False)
    version:     Mapped[int]  = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[ScheduleStatus] = mapped_column(
        SAEnum(ScheduleStatus, name="schedule_status"),
        default=ScheduleStatus.draft,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:   Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    shifts = relationship("Shift", back_populates="schedule", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("org_id", "range_start", "range_end", "version", name="uq_schedule_range_version"),
    )
