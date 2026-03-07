from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    name: str
    created_at: datetime
    deleted_at: datetime | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
