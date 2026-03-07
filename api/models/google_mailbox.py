import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class GoogleMailbox(Base):
    __tablename__ = "google_mailboxes"

    google_mailbox_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    token_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_history_id: Mapped[str | None] = mapped_column(String, nullable=True)
    watch_expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", lazy="selectin")
