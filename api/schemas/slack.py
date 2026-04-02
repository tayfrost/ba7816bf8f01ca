from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SlackWorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    team_id: str
    access_token: str


class SlackUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: str
    slack_user_id: str
    name: str
    surname: str
    created_at: datetime
    status: str
    email: str | None = None
