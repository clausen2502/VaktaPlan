from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )

    # the schedule window published
    range_start: Mapped[date] = mapped_column(Date(), nullable=False)
    range_end:   Mapped[date] = mapped_column(Date(), nullable=False)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # who published
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
