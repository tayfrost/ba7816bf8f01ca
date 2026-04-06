from pydantic import BaseModel, ConfigDict


class PlanCreate(BaseModel):
    plan_name: str
    price_pennies: int
    seat_limit: int
    currency: str = "GBP"


class PlanUpdate(BaseModel):
    plan_name: str | None = None
    price_pennies: int | None = None
    seat_limit: int | None = None
    currency: str | None = None


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    plan_name: str
    price_pennies: int
    currency: str
    seat_limit: int
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None
