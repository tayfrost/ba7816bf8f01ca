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
