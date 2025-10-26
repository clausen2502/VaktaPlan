from __future__ import annotations
from datetime import date, time
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PreferenceSchema(BaseModel):
    id: int
    employee_id: int
    weekday: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    role_id: Optional[int] = None
    location_id: Optional[int] = None
    weight: Optional[int] = None
    do_not_schedule: bool
    notes: Optional[str] = None
    active_start: Optional[date] = None
    active_end: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


# PUBLIC payload
class PreferenceCreatePayload(BaseModel):
    employee_id: int
    weekday: Optional[int] = Field(None, description="0=Mon .. 6=Sun")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    role_id: Optional[int] = None
    location_id: Optional[int] = None
    weight: Optional[int] = Field(None, description="0..5 (ignored if do_not_schedule=True)")
    do_not_schedule: bool = False
    notes: Optional[str] = None
    active_start: Optional[date] = None
    active_end: Optional[date] = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("weekday")
    @classmethod
    def weekday_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError("weekday must be between 0 (Mon) and 6 (Sun)")
        return v

    @model_validator(mode="after")
    def validate_times_and_ranges(self):
        if (self.start_time is None) ^ (self.end_time is None):
            raise ValueError("weekly timeframe is incorrect. start time and end time must be provided together")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("weekly timeframe is incorrect. start time must be before end time")

        if self.active_start and self.active_end and self.active_start > self.active_end:
            raise ValueError("preference timeframe is incorrect. start must be on or before active end")

        if self.weight is not None and not (0 <= self.weight <= 5):
            raise ValueError("weight must be between 0 and 5")
        return self


# INTERNAL DTO for the service
class PreferenceCreate(BaseModel):
    org_id: int
    employee_id: int
    weekday: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    role_id: Optional[int] = None
    location_id: Optional[int] = None
    weight: Optional[int] = None
    do_not_schedule: bool = False
    notes: Optional[str] = None
    active_start: Optional[date] = None
    active_end: Optional[date] = None


class PreferenceUpdate(BaseModel):
    weekday: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    role_id: Optional[int] = None
    location_id: Optional[int] = None
    weight: Optional[int] = None
    do_not_schedule: Optional[bool] = None
    notes: Optional[str] = None
    active_start: Optional[date] = None
    active_end: Optional[date] = None

    @field_validator("weekday")
    @classmethod
    def weekday_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError("weekday must be between 0 (Mon) and 6 (Sun)")
        return v

    @model_validator(mode="after")
    def validate_partial(self):
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise ValueError("weekly timeframe is incorrect. start time must be before end time")
        if self.active_start is not None and self.active_end is not None:
            if self.active_start > self.active_end:
                raise ValueError("preference timeframe is incorrect. active start must be on or before active end")
        if self.weight is not None and not (0 <= self.weight <= 5):
            raise ValueError("weight must be between 0 and 5")
        return self