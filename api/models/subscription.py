from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','past_due','canceled','incomplete','trialing','unpaid')",
            name="ck_subscription_status",
        ),
        CheckConstraint(
            "interval IN ('month','year')",
            name="ck_subscription_interval",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscription_plan.plan_id", ondelete="RESTRICT"), nullable=False
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

    company = relationship("Company", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", lazy="selectin")
