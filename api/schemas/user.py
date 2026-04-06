import uuid

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    company_id: int
    display_name: str | None = None
    role: str
    status: str


class UserRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    company_id: int
    display_name: str | None = None
    role: str
    status: str
    email: str = ""


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
