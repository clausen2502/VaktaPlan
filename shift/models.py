from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

if TYPE_CHECKING:
    from schedule.models import Schedule
    from jobrole.models import JobRole
    from organization.models import Organization
    from location.models import Location

class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedules.id", ondelete="CASCADE"), index=True
    )

    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_roles.id", ondelete="SET NULL"), index=True, nullable=True
    )

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # relationships
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="shifts")
    location: Mapped["Location | None"] = relationship("Location", lazy="joined", passive_deletes=True)
    role: Mapped["JobRole | None"] = relationship("JobRole")
    org: Mapped["Organization"] = relationship("Organization")

Index("ix_shifts_org_start", Shift.org_id, Shift.start_at)
Index("ix_shifts_schedule_start", Shift.schedule_id, Shift.start_at)
