from pydantic import BaseModel, ConfigDict


class PlanCreate(BaseModel):
    plan_name: str
    plan_cost_pennies: int
    currency: str = "GBP"
    max_employees: int
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None


class PlanUpdate(BaseModel):
    plan_name: str | None = None
    plan_cost_pennies: int | None = None
    currency: str | None = None
    max_employees: int | None = None
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    plan_name: str
    plan_cost_pennies: int
    currency: str
    max_employees: int
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None
