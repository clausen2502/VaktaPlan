from typing import Optional
from pydantic import BaseModel, ConfigDict

class JobRoleSchema(BaseModel):
    id: int
    org_id: int
    name: str
    weekly_hours_cap: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# PUBLIC payload, what clients send
class JobRoleCreatePayload(BaseModel):
    name: str
    weekly_hours_cap: Optional[int] = None
    model_config = ConfigDict(extra="forbid")


# INTERNAL DTO for the service 
class JobRoleCreate(BaseModel):
    org_id: int
    name: str
    weekly_hours_cap: Optional[int] = None


class JobRoleUpdate(BaseModel):
    name: Optional[str] = None
    weekly_hours_cap: Optional[int] = None

