from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublicationSchema(BaseModel):
    id: int
    org_id: int
    range_start: date
    range_end: date
    version: int
    user_id: int
    published_at: datetime
    model_config = ConfigDict(from_attributes=True)


# PUBLIC payload from clients
class PublicationCreatePayload(BaseModel):
    range_start: date = Field(..., description="Inclusive start date of the schedule window")
    range_end: date   = Field(..., description="Inclusive end date of the schedule window")
    version: Optional[int] = Field(None, description="If skipped, next version is chosen automatically")
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_dates(self):
        if self.range_start > self.range_end:
            raise ValueError("start must be on or before end")
        return self


# INTERNAL DTO for the service
class PublicationCreate(BaseModel):
    org_id: int
    user_id: int
    range_start: date
    range_end: date
    version: Optional[int] = None

    def default_published_at(self) -> datetime:
        return datetime.now(timezone.utc)
