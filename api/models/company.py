from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    __table_args__ = (
        CheckConstraint("char_length(trim(company_name)) > 1", name="ck_company_name_len"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscription_plan.plan_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stripe field (added by payments service)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)

    plan = relationship("SubscriptionPlan", lazy="selectin")
    subscriptions = relationship("Subscription", back_populates="company", lazy="selectin")
    users = relationship("User", back_populates="company", lazy="selectin")
    payments = relationship("Payment", back_populates="company", lazy="selectin")
