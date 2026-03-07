from typing import Optional

from sqlalchemy import BigInteger, CHAR, CheckConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"

    __table_args__ = (
        CheckConstraint("char_length(trim(plan_name)) > 1", name="ck_plan_name_len"),
        CheckConstraint("plan_cost_pennies >= 0", name="ck_plan_cost_nonneg"),
        CheckConstraint("max_employees > 0", name="ck_max_employees_pos"),
    )

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    plan_cost_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'GBP'"))
    max_employees: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Stripe fields (added by payments service)
    stripe_price_id_monthly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stripe_price_id_yearly: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
