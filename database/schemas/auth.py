from __future__ import annotations

from typing import Optional, List
from datetime import datetime
import uuid

from sqlalchemy import (BigInteger,Text,CHAR,
    DateTime,ForeignKey,
    ForeignKeyConstraint,CheckConstraint,
    UniqueConstraint,Index,func)

from sqlalchemy.dialects.postgresql import UUID, JSONB, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.schemas.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint("role IN ('admin','biller','viewer')", name="ck_users_role"),
        CheckConstraint("status IN ('active','inactive')", name="ck_users_status"),
        # needed for composite FKs
        UniqueConstraint("company_id", "user_id", name="uq_users_company_user"),
        Index("idx_users_company", "company_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="users")
    slack_accounts: Mapped[List["SlackAccount"]] = relationship(back_populates="user")
    google_mailboxes: Mapped[List["GoogleMailbox"]] = relationship(
    back_populates="user",
    overlaps="google_mailboxes")

    message_incidents: Mapped[List["MessageIncident"]] = relationship(
        back_populates="user",
        overlaps="message_incidents",
    )
    auth_users: Mapped[List["AuthUser"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id!r}, company_id={self.company_id!r}, role={self.role!r})"

class AuthUser(Base):
    __tablename__ = "auth_users"

    auth_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=True)

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="auth_users")
    user: Mapped[Optional["User"]] = relationship(back_populates="auth_users")

    def __repr__(self) -> str:
        return f"AuthUser(auth_user_id={self.auth_user_id!r}, email={self.email!r})"