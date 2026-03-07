from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    price_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    seat_limit: Mapped[int] = mapped_column(Integer, nullable=False)
