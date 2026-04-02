from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CHAR, CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Payment(Base):
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

    company = relationship("Company", back_populates="payments")


class StripeEvent(Base):
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
