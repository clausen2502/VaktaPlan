from pydantic import BaseModel, ConfigDict
from typing import Optional


class EmployeeRead(BaseModel):
    id: int
    org_id: int
    display_name: str
    user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class EmployeeCreatePayload(BaseModel):
    org_id: int
    display_name: str