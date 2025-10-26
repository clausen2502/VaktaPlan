from typing import Optional
from pydantic import BaseModel, ConfigDict

class OrganizationSchema(BaseModel):
    id: int
    name: str
    timezone: str
    model_config = ConfigDict(from_attributes=True)

# what clients send
class OrganizationCreatePayload(BaseModel):
    name: str
    timezone: Optional[str] = None
    model_config = ConfigDict(extra="forbid")

# internal DTO for service
class OrganizationCreate(BaseModel):
    name: str
    timezone: str = "GMT"

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
