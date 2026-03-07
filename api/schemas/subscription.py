from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    plan_name: str
    price_pennies: int
    currency: str
    seat_limit: int


class SubscriptionCreate(BaseModel):
    plan_id: int


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_id: int
    company_id: int
    plan_id: int
    status: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    created_at: datetime
