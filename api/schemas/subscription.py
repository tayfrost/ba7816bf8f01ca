from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionCreate(BaseModel):
    plan_id: int
    status: str = "trialing"
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    plan_name: str
    price_pennies: int
    currency: str
    seat_limit: int
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_id: int
    company_id: int
    plan_id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
