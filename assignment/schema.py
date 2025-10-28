from __future__ import annotations
from typing import Optional
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
