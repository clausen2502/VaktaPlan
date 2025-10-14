from datetime import datetime
from pydantic import BaseModel

class ShiftRead(BaseModel):
    id: int
    org_id: int
    location_id: int
    role_id: int
    start_at: datetime
    end_at: datetime

    class Config:
        from_attributes = True  # so we get attributes, not dict. (wouldn't even work without this)
