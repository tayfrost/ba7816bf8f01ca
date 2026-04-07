import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MessageIncidentCreate(BaseModel):
    user_id: uuid.UUID
    source: str
    sent_at: datetime
    content_raw: dict[str, Any]
    conversation_id: str | None = None
    recommendation: str | None = None


class MessageIncidentRead(BaseModel):
    """Internal schema — used by service-to-service endpoints (AI service reads message_id)."""
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    company_id: int
    user_id: uuid.UUID
    source: str
    sent_at: datetime
    content_raw: dict[str, Any]
    conversation_id: str | None = None
    recommendation: str | None = None
    created_at: datetime


class IncidentFeedItem(BaseModel):
    """Frontend-facing incident shape for the dashboard incident feed."""
    incident_id: int
    company_id: int
    team_id: str
    slack_user_id: str
    message_ts: str
    created_at: str
    channel_id: str
    raw_message_text: dict[str, Any] | None
    class_reason: str
    recommendation: str | None = None


class IncidentFeedStats(BaseModel):
    """Frontend-facing stats — groups by ML prediction category."""
    total: int
    by_reason: dict[str, int]
