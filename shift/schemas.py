# shift/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from .models import ShiftStatus

class ShiftRead(BaseModel):
    id: int
    org_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    status: ShiftStatus
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# PUBLIC body (no org_id)
class ShiftCreatePayload(BaseModel):
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime = Field(..., description="TZ-aware ISO8601")
    end_at: datetime   = Field(..., description="TZ-aware ISO8601")
    status: ShiftStatus = ShiftStatus.draft
    notes: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("start_at", "end_at")
    @classmethod
    def tz_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError("Datetime must be timezone-aware (e.g., 2025-10-16T09:00:00Z)")
        return dt

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_at <= self.start_at:
            raise ValueError("The end date must be after the start date!")
        return self


# INTERNAL DTO for the service
class ShiftCreateIn(BaseModel):
    org_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    status: ShiftStatus
    notes: Optional[str] = None


class ShiftUpdateIn(BaseModel):
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    status: Optional[ShiftStatus] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_dates_if_both_present(self):
        if self.start_at is not None and self.end_at is not None:
            if self.start_at >= self.end_at:
                raise ValueError("start_at must be before end_at")
        return self
