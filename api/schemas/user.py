from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    surname: str
    email: str


class UserRoleRead(BaseModel):
    """User info combined with their role at a specific company."""
    user_id: int
    name: str
    surname: str
    email: str
    company_id: int
    role: str
    status: str


class UserUpdate(BaseModel):
    name: str | None = None
    surname: str | None = None
