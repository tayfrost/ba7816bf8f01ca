from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class FlaggedIncident(Base):
    __tablename__ = "flagged_incidents"

    __table_args__ = (
        ForeignKeyConstraint(
            ["team_id", "slack_user_id"],
            ["slack_users.team_id", "slack_users.slack_user_id"],
            name="fk_flagged_incidents_tracker",
            ondelete="RESTRICT",
        ),
        Index("idx_flagged_incidents_company_created_at", "company_id", "created_at"),
        Index("idx_flagged_incidents_team_user_created_at", "team_id", "slack_user_id", "created_at"),
    )

    incident_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.company_id", ondelete="RESTRICT"), nullable=False,
    )
    team_id: Mapped[str] = mapped_column(
        Text, ForeignKey("slack_workspaces.team_id", ondelete="RESTRICT"), nullable=False,
    )
    slack_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_ts: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_message_text: Mapped[dict] = mapped_column(JSONB, nullable=False)
    class_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company = relationship("Company", back_populates="flagged_incidents", foreign_keys=[company_id])
    workspace = relationship(
        "SlackWorkspace",
        foreign_keys=[team_id],
        overlaps="flagged_incidents",
    )
