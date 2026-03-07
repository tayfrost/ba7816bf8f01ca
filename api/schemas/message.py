import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    company_id: int
    user_id: uuid.UUID
    source: str
    sent_at: datetime | None = None
    content_raw: dict[str, Any] | None = None
    conversation_id: str | None = None
    created_at: datetime


class IncidentScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: uuid.UUID
    neutral_score: float | None = None
    humor_sarcasm_score: float | None = None
    stress_score: float | None = None
    burnout_score: float | None = None
    depression_score: float | None = None
    harassment_score: float | None = None
    suicidal_ideation_score: float | None = None
    predicted_category: str | None = None
    predicted_severity: str | None = None
