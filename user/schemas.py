from pydantic import BaseModel, EmailStr, ConfigDict

class UserSchema(BaseModel):
    id: int
    org_id: int
    username: str
    email: EmailStr
    is_manager: bool
    model_config = ConfigDict(from_attributes=True)

class ManagerSignup(BaseModel):
    org_name: str
    username: str
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
