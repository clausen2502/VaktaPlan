from __future__ import annotations
from datetime import date, time
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ---------- DB → API (read) ----------
class WeeklyTemplateSchema(BaseModel):
    id: int
    org_id: int
    schedule_id: int
    weekday: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_time: time
    end_time: time
    required_staff_count: int = 1
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Client → API (save template) ----------
class WeeklyTemplateRowPayload(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=Mon .. 6=Sun")
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_time: time
    end_time: time
    required_staff_count: int = Field(1, ge=1)
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("end_time")
    @classmethod
    def non_zero_length(cls, v: time, info):
        st = info.data.get("start_time")
        if st and v == st:
            raise ValueError("start time and end time cannot be equal")
        return v


class WeeklyTemplateUpsertPayload(BaseModel):
    items: List[WeeklyTemplateRowPayload]
    model_config = ConfigDict(extra="forbid")


# ---------- Internal DTOs (service layer) ----------
class WeeklyTemplateRowCreate(BaseModel):
    org_id: int
    schedule_id: int
    weekday: int
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_time: time
    end_time: time
    required_staff_count: int = Field(1, ge=1)
    notes: Optional[str] = None


class WeeklyTemplateRowUpdate(BaseModel):
    weekday: Optional[int] = None
    location_id: Optional[int] = None
    role_id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    required_staff_count: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time is not None and self.end_time is not None:
            if self.end_time == self.start_time:
                raise ValueError("start time and end time cannot be equal")
        if self.weekday is not None and not (0 <= self.weekday <= 6):
            raise ValueError("weekday must be between 0 and 6")
        return self


# ---------- Client → API (generate shifts) ----------
class WeeklyTemplateGeneratePayload(BaseModel):
    start_date: date
    end_date: date
    policy: Literal["replace", "fill_missing"] = "replace"
    model_config = ConfigDict(extra="forbid")
    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on/after start_date")
        return self

