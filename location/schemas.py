from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, FieldValidationInfo, model_validator

class LocationRead(BaseModel):
    id: int
    org_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class LocationCreateIn(BaseModel):
    org_id: int
    name: str

class LocationUpdateIn(BaseModel):
    name: Optional[str] = None
