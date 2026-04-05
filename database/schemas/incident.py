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
