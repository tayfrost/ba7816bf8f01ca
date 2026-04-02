from typing import List
from typing import Optional
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index
from sqlalchemy import BigInteger, Text, CHAR, String, CheckConstraint, DateTime,func, text, UniqueConstraint,and_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB



class Base(DeclarativeBase):
    pass

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"

    __table_args__ = (
            CheckConstraint("char_length(trim(plan_name)) > 1", name="ck_plan_name_len"),
            CheckConstraint("plan_cost_pennies >= 0", name="ck_plan_cost_nonneg"),
            CheckConstraint("max_employees > 0", name="ck_max_employees_pos"),
        )

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_name: Mapped[str] = mapped_column(Text, nullable = False, unique=True)
    plan_cost_pennies: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default= text("'GBP'"))
    max_employees: Mapped[int] = mapped_column(BigInteger, nullable=False)

    companies: Mapped[List["Company"]] = relationship(back_populates="plan")

    def __repr__(self) -> str:
        return (
            "SubscriptionPlan("
            f"plan_id={self.plan_id!r}, "
            f"plan_name={self.plan_name!r}, "
            f"plan_cost_pennies={self.plan_cost_pennies!r}, "
            f"currency={self.currency!r}, "
            f"max_employees={self.max_employees!r}"
            ")"
        )

class Company(Base):
    __tablename__ = "companies"

    __table_args__ = (CheckConstraint("char_length(trim(company_name)) > 1", name="ck_company_name_len"),)

    company_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("subscription_plan.plan_id", ondelete="RESTRICT"),
                                          nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False, server_default=func.now())
    company_name: Mapped[str] = mapped_column(Text, nullable = False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),nullable=True)

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="companies")
    company_roles: Mapped[list["SaasCompanyRole"]] = relationship(back_populates="company")
    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="company")
    flagged_incidents: Mapped[list["FlaggedIncident"]] = relationship(back_populates="company")

    def __repr__(self) -> str:
        return f"Company(company_id={self.company_id!r}, company_name={self.company_name!r}, plan_id={self.plan_id!r})"

class SaasUserData(Base):
    __tablename__ = "saas_user_data"

    __table_args__ = (
            CheckConstraint("char_length(trim(name)) > 1", name="ck_saas_name_len"),
            CheckConstraint("char_length(trim(surname)) > 1", name="ck_saas_surname_len"),
            CheckConstraint("char_length(trim(email)) > 3 AND position('@' in trim(email)) > 1 AND position('@' in trim(email)) < char_length(trim(email))", name="ck_saas_email")
        )
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable = False)
    surname: Mapped[str] = mapped_column(Text, nullable = False)
    email: Mapped[str] = mapped_column(Text, nullable = False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable = False)
    
    company_roles: Mapped[list["SaasCompanyRole"]] = relationship(back_populates="user")
    def __repr__(self) -> str:
        return (
            "SaasUserData("
            f"user_id={self.user_id!r}, "
            f"name={self.name!r}, "
            f"surname={self.surname!r}, "
            f"email={self.email!r}"
            ")"
        )

class SaasCompanyRole(Base):
    __tablename__ = "saas_company_roles"

    __table_args__ = (
        CheckConstraint("role IN ('admin','viewer','biller')", name="ck_company_role"),
        CheckConstraint("status IN ('active','inactive','removed')", name="ck_company_role_status"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("companies.company_id", ondelete="RESTRICT"),
                                            primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("saas_user_data.user_id", ondelete="RESTRICT"),
                                            primary_key=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="company_roles")
    user: Mapped["SaasUserData"] = relationship(back_populates="company_roles")

    def __repr__(self) -> str:
        return (
            "SaasCompanyRole("
            f"company_id={self.company_id!r}, "
            f"user_id={self.user_id!r}, "
            f"role={self.role!r}, "
            f"status={self.status!r}"
            ")"
        )

class Workspace(Base):
    __tablename__ = "slack_workspaces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.company_id", ondelete="RESTRICT"),
        nullable=False,
    )

    team_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="workspaces")
    slack_users: Mapped[list["SlackUser"]] = relationship(back_populates="workspace")
    flagged_incidents: Mapped[list["FlaggedIncident"]] = relationship(back_populates="workspace")

    def __repr__(self) -> str:
        return (
            "Workspace("
            f"id={self.id!r}, "
            f"company_id={self.company_id!r}, "
            f"team_id={self.team_id!r}"
            ")"
        )
   
class SlackUser(Base):
    __tablename__ = "slack_users"

    __table_args__ = (
        CheckConstraint("char_length(trim(name)) > 1", name="ck_slack_user_name_len"),
        CheckConstraint("char_length(trim(surname)) > 1", name="ck_slack_user_surname_len"),
        CheckConstraint("status IN ('active','inactive','removed')", name="ck_slack_user_status"),
        UniqueConstraint("team_id", "slack_user_id", name="uq_slack_users_team_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    team_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("slack_workspaces.team_id", ondelete="RESTRICT"),
        nullable=False,
    )

    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    surname: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(Text, nullable=False)

    workspace: Mapped["Workspace"] = relationship(back_populates="slack_users")
    flagged_incidents: Mapped[list["FlaggedIncident"]] = relationship("FlaggedIncident",
                primaryjoin=lambda: and_(
                    SlackUser.team_id == FlaggedIncident.team_id,
                    SlackUser.slack_user_id == FlaggedIncident.slack_user_id),
                back_populates="slack_user",
                foreign_keys=lambda: [FlaggedIncident.team_id, FlaggedIncident.slack_user_id],
                overlaps="workspace,flagged_incidents")

    def __repr__(self) -> str:
        return (
            "SlackUser("
            f"id={self.id!r}, "
            f"team_id={self.team_id!r}, "
            f"slack_user_id={self.slack_user_id!r}, "
            f"status={self.status!r}"
            ")"
        )
    
class FlaggedIncident(Base):
    __tablename__ = "flagged_incidents"
    __table_args__ = (
        ForeignKeyConstraint(["team_id", "slack_user_id"],["slack_users.team_id", "slack_users.slack_user_id"],
            name="fk_flagged_incidents_tracker",
            ondelete="RESTRICT",),
        Index("idx_flagged_incidents_company_created_at", "company_id", "created_at"),
        Index("idx_flagged_incidents_team_user_created_at", "team_id", "slack_user_id", "created_at"),
    )

    incident_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"),
                                             nullable=False,)
    team_id: Mapped[str] = mapped_column(Text, ForeignKey("slack_workspaces.team_id", ondelete="RESTRICT"),
        nullable=False,)
    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_ts: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        server_default=func.now(),)
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_message_text: Mapped[dict] = mapped_column(JSONB, nullable=False)
    class_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    
    company: Mapped["Company"] = relationship(back_populates="flagged_incidents", foreign_keys=[company_id])

    workspace: Mapped["Workspace"] = relationship(back_populates="flagged_incidents",
            foreign_keys=[team_id],
            overlaps="slack_user,flagged_incidents")

    slack_user: Mapped["SlackUser"] = relationship("SlackUser",
                primaryjoin=lambda: and_(
                    FlaggedIncident.team_id == SlackUser.team_id,
                    FlaggedIncident.slack_user_id == SlackUser.slack_user_id),
                back_populates="flagged_incidents",
                foreign_keys=lambda: [FlaggedIncident.team_id, FlaggedIncident.slack_user_id],
                overlaps="workspace,flagged_incidents")
    
    message_details: Mapped[Optional["MessageDetails"]] = relationship(
        "MessageDetails",
        back_populates="flagged_incident",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    
    def __repr__(self) -> str:
        return (
            "FlaggedIncident("
            f"incident_id={self.incident_id!r}, "
            f"company_id={self.company_id!r}, "
            f"team_id={self.team_id!r}, "
            f"slack_user_id={self.slack_user_id!r}, "
            f"channel_id={self.channel_id!r}, "
            f"created_at={self.created_at!r}"
            ")"
        )

class MessageDetails(Base):
    """
    Stores the AI agent's category scores + predicted labels for a flagged incident.
    1 row per flagged_incidents.incident_id (enforced via UNIQUE).
    """
    __tablename__ = "message_details"

    __table_args__ = (
        UniqueConstraint("incident_id", name="uq_message_details_incident"),

        ForeignKeyConstraint(
            ["team_id", "slack_user_id"],
            ["slack_users.team_id", "slack_users.slack_user_id"],
            name="fk_message_details_user",
            ondelete="RESTRICT",
        ),

        Index("idx_message_details_team_user", "team_id", "slack_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    incident_id: Mapped[int] = mapped_column(BigInteger,
        ForeignKey("flagged_incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
    )

    team_id: Mapped[str] = mapped_column(Text, nullable=False)
    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)

    # mental category scores
    neutral_score: Mapped[float] = mapped_column(nullable=False)
    humor_sarcasm_score: Mapped[float] = mapped_column(nullable=False)
    stress_score: Mapped[float] = mapped_column(nullable=False)
    burnout_score: Mapped[float] = mapped_column(nullable=False)
    depression_score: Mapped[float] = mapped_column(nullable=False)
    harassment_score: Mapped[float] = mapped_column(nullable=False)
    suicidal_ideation_score: Mapped[float] = mapped_column(nullable=False)

    predicted_category: Mapped[Optional[int]] = mapped_column(nullable=True)
    predicted_severity: Mapped[Optional[int]] = mapped_column(nullable=True)

    flagged_incident: Mapped["FlaggedIncident"] = relationship(
        "FlaggedIncident",
        back_populates="message_details",
        foreign_keys=[incident_id],
        uselist=False,  # one-to-one
    )

    slack_user: Mapped["SlackUser"] = relationship(
        "SlackUser",
        primaryjoin=lambda: and_(
            MessageDetails.team_id == SlackUser.team_id,
            MessageDetails.slack_user_id == SlackUser.slack_user_id,
        ),
        foreign_keys=lambda: [MessageDetails.team_id, MessageDetails.slack_user_id],
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            "MessageDetails("
            f"id={self.id!r}, "
            f"incident_id={self.incident_id!r}, "
            f"team_id={self.team_id!r}, "
            f"slack_user_id={self.slack_user_id!r}"
            ")"
        )