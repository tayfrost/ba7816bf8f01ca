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

class MessageIncident(Base):
    __tablename__ = "message_incidents"

    __table_args__ = (
        CheckConstraint("source IN ('slack','gmail')", name="ck_message_incidents_source"),
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["users.company_id", "users.user_id"],
            name="fk_message_incidents_company_user",
            ondelete="RESTRICT",
        ),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    source: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    content_raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    company: Mapped["Company"] = relationship(
    back_populates="message_incidents",
    overlaps="message_incidents")

    user: Mapped["User"] = relationship(
        back_populates="message_incidents",
        primaryjoin="and_(MessageIncident.company_id==User.company_id, MessageIncident.user_id==User.user_id)",
        overlaps="company,message_incidents",
    )

    incident_scores: Mapped[Optional["IncidentScores"]] = relationship(
        back_populates="message_incident",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"MessageIncident(message_id={self.message_id!r}, company_id={self.company_id!r}, user_id={self.user_id!r})"

class IncidentScores(Base):
    __tablename__ = "incident_scores"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_incidents.message_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    neutral_score: Mapped[float] = mapped_column(nullable=False)
    humor_sarcasm_score: Mapped[float] = mapped_column(nullable=False)
    stress_score: Mapped[float] = mapped_column(nullable=False)
    burnout_score: Mapped[float] = mapped_column(nullable=False)
    depression_score: Mapped[float] = mapped_column(nullable=False)
    harassment_score: Mapped[float] = mapped_column(nullable=False)
    suicidal_ideation_score: Mapped[float] = mapped_column(nullable=False)

    predicted_category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    predicted_severity: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message_incident: Mapped["MessageIncident"] = relationship(back_populates="incident_scores")

    def __repr__(self) -> str:
        return f"IncidentScores(id={self.id!r}, message_id={self.message_id!r})"

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


