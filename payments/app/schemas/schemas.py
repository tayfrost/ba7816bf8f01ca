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
# Refunds
# ──────────────────────────────────────────────

class RefundCreate(BaseModel):
    payment_id: int = Field(..., description="Internal DB payment ID to refund")
    amount_pennies: Optional[int] = Field(
        None,
        description="Amount to refund in pennies. Omit for full refund.",
        ge=1,
    )
    reason: Optional[str] = Field(
        None,
        pattern="^(duplicate|fraudulent|requested_by_customer)$",
        description="Stripe refund reason: duplicate | fraudulent | requested_by_customer",
    )


class RefundResponse(BaseModel):
    payment_id: int
    stripe_refund_id: str
    amount_pennies: int
    currency: str
    status: str
    reason: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Customer Portal
# ──────────────────────────────────────────────

class CustomerPortalResponse(BaseModel):
    portal_url: str


# ──────────────────────────────────────────────
# Invoices
# ──────────────────────────────────────────────

class InvoiceLineItem(BaseModel):
    description: str
    amount_pennies: int
    currency: str


class InvoiceResponse(BaseModel):
    stripe_invoice_id: str
    number: Optional[str] = None
    status: str                          # draft | open | paid | uncollectible | void
    amount_due_pennies: int
    amount_paid_pennies: int
    currency: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    invoice_pdf: Optional[str] = None   # direct PDF download URL
    hosted_invoice_url: Optional[str] = None  # Stripe-hosted payment page
    lines: list[InvoiceLineItem] = []


class UpcomingInvoiceResponse(BaseModel):
    amount_due_pennies: int
    currency: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    lines: list[InvoiceLineItem] = []


# ──────────────────────────────────────────────
# Generic
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
