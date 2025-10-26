from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class UnavailabilitySchema(BaseModel):
    id: int
    employee_id: int
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# PUBLIC payload (what clients send)
class UnavailabilityCreatePayload(BaseModel):
    employee_id: int
    start_at: datetime = Field(..., description="ISO8601, timezone-aware")
    end_at:   datetime = Field(..., description="ISO8601, timezone-aware")
    reason: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_window(self):
        if self.start_at >= self.end_at:
            raise ValueError("start at must be before end at")
        return self


# INTERNAL DTO for the service
class UnavailabilityCreate(BaseModel):
    org_id: int
    employee_id: int
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None


class UnavailabilityUpdate(BaseModel):
    start_at: Optional[datetime] = None
    end_at:   Optional[datetime] = None
    reason:   Optional[str] = None

    @model_validator(mode="after")
    def validate_partial_window(self):
        # Only validate if both ends provided
        if self.start_at is not None and self.end_at is not None:
            if self.start_at >= self.end_at:
                raise ValueError("start at must be before end at")
        return self
