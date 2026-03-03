"""
Workspace data schema for storing OAuth credentials.
"""

from pydantic import BaseModel


class WorkspaceCredentials(BaseModel):
    team_id: str
    access_token: str
