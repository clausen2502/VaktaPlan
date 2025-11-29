from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .models import ScheduleStatus

class ScheduleSchema(BaseModel):
    id: int
    org_id: int
    name: str
    range_start: date
    range_end: date
    version: int
    status: ScheduleStatus
    created_by: Optional[int] = None
    published_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ScheduleCreatePayload(BaseModel):
    name: str = Field(..., description="Name for this schedule")
    range_start: date = Field(..., description="Inclusive start date of the schedule window")
    range_end: date   = Field(..., description="Inclusive end date of the schedule window")
    version: Optional[int] = Field(None, description="If omitted, next version is chosen automatically")
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_dates(self):
        if self.range_start > self.range_end:
            raise ValueError("start must be on or before end")
        return self

class ScheduleCreate(BaseModel):
    org_id: int
    name: str
    created_by: int
    range_start: date
    range_end: date
    version: Optional[int] = None

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    range_start: Optional[date] = None
    range_end: Optional[date] = None
    status: Optional[str] = None
    version: Optional[int] = None