from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    plan_name: str
    plan_cost_pennies: int
    currency: str
    max_employees: int
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None


class SubscriptionCreate(BaseModel):
    plan_id: int
    interval: str = "month"


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    plan_id: int
    stripe_subscription_id: str | None = None
    status: str
    interval: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
