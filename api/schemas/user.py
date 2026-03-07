import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    company_id: int
    display_name: str | None = None
    role: str
    status: str
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    status: str | None = None
