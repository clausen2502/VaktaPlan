from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

class ShiftSchema(BaseModel):
    id: int
    org_id: int
    schedule_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    notes: Optional[str] = None
    required_staff_count: int = 1

    model_config = ConfigDict(from_attributes=True)

class ShiftCreatePayload(BaseModel):
    schedule_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime = Field(..., description="TZ-aware ISO8601")
    end_at: datetime = Field(..., description="TZ-aware ISO8601")
    notes: Optional[str] = None
    required_staff_count: int = Field(1, ge=1)

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
            raise ValueError("end_at must be after start_at")
        return self

# Internal DTO the service uses
class ShiftCreate(BaseModel):
    org_id: int
    schedule_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    notes: Optional[str] = None
    required_staff_count: int = Field(1, ge=1)

class ShiftUpdate(BaseModel):
    schedule_id: Optional[int] = None
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    notes: Optional[str] = None
    required_staff_count: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def check_dates_if_both_present(self):
        if self.start_at is not None and self.end_at is not None and self.start_at >= self.end_at:
            raise ValueError("start_at must be before end_at")
        return self
