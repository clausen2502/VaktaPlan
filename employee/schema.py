from pydantic import BaseModel, ConfigDict
from typing import Optional


class EmployeeSchema(BaseModel):
    id: int
    org_id: int
    display_name: str
    user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# PUBLIC payload, what clients send
class EmployeeCreatePayload(BaseModel):
    display_name: str
    user_id: Optional[int] = None
    model_config = ConfigDict(extra="forbid")


# INTERNAL DTO for the service
class EmployeeCreate(BaseModel):
    org_id: int
    display_name: str
    user_id: Optional[int] = None

class EmployeeUpdate(BaseModel):
    display_name: str
    user_id: Optional[int] = None
