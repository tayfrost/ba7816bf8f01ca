from __future__ import annotations

from typing import Optional, List
from datetime import datetime
import uuid

from sqlalchemy import (BigInteger,Text,CHAR,
    DateTime,ForeignKey,
    ForeignKeyConstraint,CheckConstraint,
    UniqueConstraint,Index,func)

from sqlalchemy.dialects.postgresql import UUID, JSONB, CITEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship



class Base(DeclarativeBase):
    pass

class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Stripe field (added by payments service) ---
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="company")
    users: Mapped[List["User"]] = relationship(back_populates="company")
    slack_workspaces: Mapped[List["SlackWorkspace"]] = relationship(back_populates="company")
    google_mailboxes: Mapped[List["GoogleMailbox"]] = relationship(back_populates="company")
    auth_users: Mapped[List["AuthUser"]] = relationship(back_populates="company")
    message_incidents: Mapped[List["MessageIncident"]] = relationship(back_populates="company")

    def __repr__(self) -> str:
        return f"Company(company_id={self.company_id!r}, name={self.name!r})"

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    __table_args__ = (
        CheckConstraint("price_pennies >= 0", name="ck_subscription_plans_price_nonneg"),
        CheckConstraint("seat_limit > 0", name="ck_subscription_plans_seat_limit_pos"),
    )

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    price_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="GBP")
    seat_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # --- Stripe fields (added by payments service) ---
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stripe_price_id_yearly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")

    def __repr__(self) -> str:
        return f"SubscriptionPlan(plan_id={self.plan_id!r}, plan_name={self.plan_name!r})"
    
class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        CheckConstraint("status IN ('trialing','active','past_due','canceled')", name="ck_subscriptions_status"),
        # one user per company not one user multiple companies
        UniqueConstraint("company_id", name="uq_subscriptions_one_per_company"),
    )

    subscription_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscription_plans.plan_id", ondelete="RESTRICT"), nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"Subscription(subscription_id={self.subscription_id!r}, company_id={self.company_id!r}, status={self.status!r})"
