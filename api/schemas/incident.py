from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FlaggedIncidentCreate(BaseModel):
    team_id: str
    slack_user_id: str
    message_ts: str
    channel_id: str
    raw_message_text: dict[str, Any]
    class_reason: str | None = None
    recommendation: str | None = None


class FlaggedIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: int
    company_id: int
    team_id: str
    slack_user_id: str
    message_ts: str
    created_at: datetime
    channel_id: str
    raw_message_text: dict[str, Any]
    class_reason: str | None = None
    recommendation: str | None = None
