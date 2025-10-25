from typing import Optional
from pydantic import BaseModel, ConfigDict

class LocationSchema(BaseModel):
    id: int
    org_id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

# PUBLIC payload, what clients send
class LocationCreatePayload(BaseModel):
    name: str
    model_config = ConfigDict(extra="forbid")


# INTERNAL DTO for the service 
class LocationCreate(BaseModel):
    org_id: int
    name: str

class LocationUpdate(BaseModel):
    name: Optional[str] = None

class LocationCreateIn(LocationCreatePayload): pass ## for testing purposes
class LocationUpdateIn(LocationUpdate): pass ## for testing purposes
