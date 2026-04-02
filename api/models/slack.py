from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False,
    )
    team_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)

    company = relationship("Company", back_populates="workspaces")
    slack_users = relationship("SlackUser", back_populates="workspace", lazy="selectin")


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
        Text, ForeignKey("slack_workspaces.team_id", ondelete="RESTRICT"), nullable=False,
    )
    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    surname: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(Text, nullable=False)

    workspace = relationship("SlackWorkspace", back_populates="slack_users")
