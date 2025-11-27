from __future__ import annotations
from datetime import date
from typing import Optional
from typing_extensions import Literal
from pydantic import BaseModel, ConfigDict


class AssignmentSchema(BaseModel):
    shift_id: int
    employee_id: int
    model_config = ConfigDict(from_attributes=True)


# PUBLIC payload from clients
class AssignmentCreatePayload(BaseModel):
    shift_id: int
    employee_id: int
    model_config = ConfigDict(extra="forbid")


# INTERNAL DTO for the service
class AssignmentCreate(BaseModel):
    org_id: int
    shift_id: int
    employee_id: int
    preference_score: Optional[int] = None


class AssignmentUpdate(BaseModel):
    preference_score: Optional[int] = None

class AutoAssignRequest(BaseModel):
    schedule_id: int
    start_date: date
    end_date: date
    policy: Literal["fill_missing", "reassign_all"] = "fill_missing"
    dry_run: bool = False


class AutoAssignResponse(BaseModel):
    assigned: int
    skipped_full: int
    skipped_no_candidates: int
    policy: str