import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    slack_workspace_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id"), nullable=False)
    team_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", lazy="selectin")
    accounts = relationship("SlackAccount", back_populates="workspace", lazy="selectin")


class SlackAccount(Base):
    __tablename__ = "slack_accounts"
    __table_args__ = (UniqueConstraint("team_id", "slack_user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("slack_workspaces.team_id"), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id"), nullable=False)

    workspace = relationship("SlackWorkspace", back_populates="accounts")
