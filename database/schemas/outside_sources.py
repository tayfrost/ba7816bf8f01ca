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


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    __table_args__ = (
        UniqueConstraint("team_id", name="uq_slack_workspaces_team_id"),
        UniqueConstraint("company_id", "team_id", name="uq_slack_workspaces_company_team"),
        Index("idx_slack_workspaces_company", "company_id"),
    )

    slack_workspace_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)

    team_id: Mapped[str] = mapped_column(Text, nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)

    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="slack_workspaces")
    slack_accounts: Mapped[List["SlackAccount"]] = relationship(
    back_populates="workspace",
    overlaps="slack_accounts")

    def __repr__(self) -> str:
        return f"SlackWorkspace(slack_workspace_id={self.slack_workspace_id!r}, team_id={self.team_id!r})"


class SlackAccount(Base):
    __tablename__ = "slack_accounts"

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "team_id"],
            ["slack_workspaces.company_id", "slack_workspaces.team_id"],
            name="fk_slack_accounts_company_team",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["users.company_id", "users.user_id"],
            name="fk_slack_accounts_company_user",
            ondelete="RESTRICT",
        ),
        Index("idx_slack_accounts_user", "user_id"),
        Index("idx_slack_accounts_company", "company_id"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    team_id: Mapped[str] = mapped_column(Text, nullable=False)
    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    email: Mapped[Optional[str]] = mapped_column(CITEXT, nullable=True)

    __mapper_args__ = {"primary_key": [team_id, slack_user_id]}

    workspace: Mapped["SlackWorkspace"] = relationship(
    back_populates="slack_accounts",
    primaryjoin="and_(SlackAccount.company_id==SlackWorkspace.company_id, SlackAccount.team_id==SlackWorkspace.team_id)",
    overlaps="slack_accounts")

    user: Mapped["User"] = relationship(
        back_populates="slack_accounts",
        primaryjoin="and_(SlackAccount.company_id==User.company_id, SlackAccount.user_id==User.user_id)",
        overlaps="slack_accounts,workspace")

    def __repr__(self) -> str:
        return f"SlackAccount(team_id={self.team_id!r}, slack_user_id={self.slack_user_id!r}, user_id={self.user_id!r})"


class GoogleMailbox(Base):
    __tablename__ = "google_mailboxes"

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["users.company_id", "users.user_id"],
            name="fk_google_mailboxes_company_user",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("company_id", "email_address", name="uq_google_mailboxes_company_email"),
        Index("idx_google_mailboxes_company", "company_id"),
    )

    google_mailbox_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    email_address: Mapped[str] = mapped_column(CITEXT, nullable=False)

    token_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    last_history_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    watch_expiration: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(
    back_populates="google_mailboxes",
    overlaps="google_mailboxes")

    user: Mapped["User"] = relationship(
        back_populates="google_mailboxes",
        primaryjoin="and_(GoogleMailbox.company_id==User.company_id, GoogleMailbox.user_id==User.user_id)",
        overlaps="company,google_mailboxes")

    def __repr__(self) -> str:
        return f"GoogleMailbox(google_mailbox_id={self.google_mailbox_id!r}, email_address={self.email_address!r})"
