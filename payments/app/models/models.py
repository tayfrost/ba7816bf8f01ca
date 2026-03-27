"""
SQLAlchemy ORM models for the payments domain.

IMPORTANT: This service shares the database with the core backend (Derja's schema).
- `subscription_plans` and `companies` are defined in database/new_database/new_oop.py
- We only EXTEND them here (add Stripe columns) and define NEW payment-specific tables.
- NEW tables: stripe_subscriptions, payments, stripe_events
- Extended: subscription_plans (+ stripe price IDs), companies (+ stripe_customer_id)
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    CheckConstraint,
    CHAR,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class StripeSubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"


# ──────────────────────────────────────────────
# EXISTING tables (mirrors of Derja's schema)
# We re-declare them so SQLAlchemy knows about them,
# but we do NOT create them — they already exist.
# ──────────────────────────────────────────────

class SubscriptionPlan(Base):
    """
    Mirrors database/new_database/new_oop.py SubscriptionPlan.
    Table name: subscription_plans (with 's')
    Added: stripe_price_id_monthly, stripe_price_id_yearly
    """
    __tablename__ = "subscription_plans"
    __table_args__ = ({"extend_existing": True},)

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    price_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'GBP'"))
    seat_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # --- Stripe fields (added by payments service) ---
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stripe_price_id_yearly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    stripe_subscriptions: Mapped[list["StripeSubscription"]] = relationship(back_populates="plan")


class Company(Base):
    """
    Mirrors database/new_database/new_oop.py Company.
    Column 'name' (not 'company_name') — matches Derja's schema.
    Added: stripe_customer_id
    """
    __tablename__ = "companies"
    __table_args__ = ({"extend_existing": True},)

    company_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Stripe field (added by payments service) ---
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)

    # Relationships
    stripe_subscriptions: Mapped[list["StripeSubscription"]] = relationship(back_populates="company")
    payments: Mapped[list["Payment"]] = relationship(back_populates="company")


# ──────────────────────────────────────────────
# NEW tables (created by payments service)
# ──────────────────────────────────────────────

class StripeSubscription(Base):
    """
    Stripe-specific subscription data.
    Named 'stripe_subscriptions' to avoid conflict with Derja's 'subscriptions' table.
    """
    __tablename__ = "stripe_subscriptions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','past_due','canceled','incomplete','trialing','unpaid')",
            name="ck_stripe_subscription_status",
        ),
        CheckConstraint(
            "interval IN ('month','year')",
            name="ck_stripe_subscription_interval",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscription_plans.plan_id", ondelete="RESTRICT"), nullable=False
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'incomplete'"))
    interval: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'month'"))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="stripe_subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="stripe_subscriptions")


class Payment(Base):
    """Individual payment / invoice record."""
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded','pending','failed','refunded')",
            name="ck_payment_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    amount_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'GBP'"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="payments")


class StripeEvent(Base):
    """Idempotency log — every processed Stripe webhook event."""
    __tablename__ = "stripe_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stripe_event_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
