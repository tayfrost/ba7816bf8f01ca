import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SlackWorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slack_workspace_id: int
    company_id: int
    team_id: str
    access_token: str
    installed_at: datetime
    revoked_at: datetime | None = None


class SlackAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    team_id: str
    slack_user_id: str
    user_id: uuid.UUID
    email: str | None = None
