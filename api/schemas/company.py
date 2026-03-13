from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    company_name: str
    plan_id: int


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    plan_id: int
    company_name: str
    created_at: datetime
    deleted_at: datetime | None = None
    stripe_customer_id: str | None = None


class CompanyUpdate(BaseModel):
    company_name: str | None = None
