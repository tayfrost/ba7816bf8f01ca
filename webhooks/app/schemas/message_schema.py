"""
Message data schema for storing Slack message events.
"""

from pydantic import BaseModel


class MessageEvent(BaseModel):
    team_id: str
    user_id: str
    text: str
    timestamp: str
