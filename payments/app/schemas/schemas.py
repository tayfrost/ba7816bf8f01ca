"""
Pydantic schemas for API request / response validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────
# Organization
# ──────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Acme Corp"])
    email: EmailStr = Field(..., examples=["billing@acme.com"])
    employee_count: Optional[int] = Field(None, ge=1, examples=[50])


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    email: str
    stripe_customer_id: Optional[str] = None
    is_active: bool
    employee_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Subscription Plans
# ──────────────────────────────────────────────

class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price_monthly: Decimal
    price_yearly: Decimal
    max_employees: int
    features: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Checkout / Subscription
# ──────────────────────────────────────────────

class CheckoutSessionCreate(BaseModel):
    organization_id: UUID
    plan_id: UUID
    interval: str = Field("month", pattern="^(month|year)$")


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    plan_id: UUID
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
        description="If true, subscription stays active until the end of the billing period."
    )


# ──────────────────────────────────────────────
# Payments
# ──────────────────────────────────────────────

class PaymentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    stripe_payment_intent_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    amount: Decimal
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
