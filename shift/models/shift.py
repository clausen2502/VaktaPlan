from __future__ import annotations

from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, Text, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class ShiftStatus(str, Enum):
    draft = "draft"
    published = "published"

class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(primary_key=True)

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_roles.id", ondelete="SET NULL"), index=True, nullable=True
    )

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[ShiftStatus] = mapped_column(
        SAEnum(ShiftStatus, name="shift_status"), nullable=False, default=ShiftStatus.draft
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # relationships
    location = relationship("Location", lazy="joined", passive_deletes=True)
    role: Mapped[JobRole | None] = relationship("JobRole")
    org: Mapped[Organization] = relationship("Organization")

# helpful composite index: org + start time
Index("ix_shifts_org_start", Shift.org_id, Shift.start_at)
