from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, FieldValidationInfo, model_validator
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

class ShiftCreateIn(BaseModel):
    org_id: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: datetime = Field(..., description="Timezone-aware ISO8601 (2025-10-16T09:00:00Z)")
    end_at: datetime   = Field(..., description="Timezone-aware ISO8601 (2025-10-16T09:00:00Z)")
    status: ShiftStatus = ShiftStatus.draft
    notes: Optional[str] = None
    
    @field_validator("start_at", "end_at")
    @classmethod
    def tz_aware(classmethod, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("Datetime must be timezone-aware (2025-10-16T09:00:00Z)")
        return value

    @field_validator("end_at")
    @classmethod
    def end_after_start(cls, end: datetime, info: FieldValidationInfo) -> datetime:
        start = info.data.get("start_at")
        if start and end <= start:
            raise ValueError("The end date must be after the start date!")
        return end

class ShiftUpdateIn(BaseModel):
    org_id: Optional[int] = None
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    status: Optional[ShiftStatus] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_dates_if_both_present(self):
        # Only validate ordering if BOTH are provided.
        if self.start_at is not None and self.end_at is not None:
            if self.start_at >= self.end_at:
                raise ValueError("start_at must be before end_at")
        return self