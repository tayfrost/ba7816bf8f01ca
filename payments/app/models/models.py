"""
SQLAlchemy ORM models for the payments domain.
Tables: organizations, subscription_plans, subscriptions, payments, stripe_events
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class SubscriptionStatus(str, enum.Enum):
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


class PlanInterval(str, enum.Enum):
    MONTH = "month"
    YEAR = "year"


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class Organization(Base):
    """Company that subscribes to SentinelAI."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    stripe_customer_id = Column(String(255), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    employee_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="organization", lazy="selectin")
    payments = relationship("Payment", back_populates="organization", lazy="selectin")


class SubscriptionPlan(Base):
    """Available pricing tiers (seeded on startup)."""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2), nullable=False)
    max_employees = Column(Integer, nullable=False)
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_yearly = Column(String(255), nullable=True)
    features = Column(Text, nullable=True)  # JSON-encoded feature list
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan", lazy="selectin")


class Subscription(Base):
    """Active subscription linking an organization to a plan."""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)
    interval = Column(Enum(PlanInterval), default=PlanInterval.MONTH)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")


class Payment(Base):
    """Individual payment / invoice record."""
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    stripe_invoice_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="gbp")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="payments")


class StripeEvent(Base):
    """Idempotency log — every processed Stripe webhook event."""
    __tablename__ = "stripe_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(255), nullable=False)
    processed = Column(Boolean, default=False)
    payload = Column(Text, nullable=True)  # Raw JSON for debugging
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("stripe_event_id", name="uq_stripe_event_id"),
    )
