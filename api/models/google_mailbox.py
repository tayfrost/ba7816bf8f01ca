from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class GoogleMailbox(Base):
    __tablename__ = "google_mailboxes"

    google_mailbox_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("saas_user_data.user_id"), nullable=True)
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    token_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_history_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    watch_expiration: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", lazy="selectin")
