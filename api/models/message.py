import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.company_id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)  # slack, gmail
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scores = relationship("IncidentScore", back_populates="message", lazy="selectin")


class IncidentScore(Base):
    __tablename__ = "incident_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.message_id"), nullable=False)
    neutral_score: Mapped[float] = mapped_column(Float, nullable=True)
    humor_sarcasm_score: Mapped[float] = mapped_column(Float, nullable=True)
    stress_score: Mapped[float] = mapped_column(Float, nullable=True)
    burnout_score: Mapped[float] = mapped_column(Float, nullable=True)
    depression_score: Mapped[float] = mapped_column(Float, nullable=True)
    harassment_score: Mapped[float] = mapped_column(Float, nullable=True)
    suicidal_ideation_score: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_category: Mapped[str | None] = mapped_column(String, nullable=True)
    predicted_severity: Mapped[str | None] = mapped_column(String, nullable=True)

    message = relationship("Message", back_populates="scores")
