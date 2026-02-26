"""
Pydantic schemas for API request / response validation.
Aligned with shared database schema (companies, subscription_plan).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────
# Subscription Plans
# ──────────────────────────────────────────────

class SubscriptionPlanResponse(BaseModel):
    plan_id: int
    plan_name: str
    plan_cost_pennies: int
    currency: str
    max_employees: int
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Checkout / Subscription
# ──────────────────────────────────────────────

class CheckoutSessionCreate(BaseModel):
    company_id: int
    plan_id: int
    interval: str = Field("month", pattern="^(month|year)$")


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    id: int
    company_id: int
    plan_id: int
    stripe_subscription_id: Optional[str] = None
    status: str
    interval: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCancel(BaseModel):
    cancel_at_period_end: bool = Field(
        True,
        description="If true, subscription stays active until the end of the billing period.",
    )


# ──────────────────────────────────────────────
# Payments
# ──────────────────────────────────────────────

class PaymentResponse(BaseModel):
    id: int
    company_id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    amount_pennies: int
    currency: str
    status: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Customer Portal
# ──────────────────────────────────────────────

class CustomerPortalResponse(BaseModel):
    portal_url: str


# ──────────────────────────────────────────────
# Generic
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
