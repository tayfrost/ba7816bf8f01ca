"""
OAuth Service

Handles OAuth flow business logic including processing OAuth responses
and storing workspace credentials.
"""

import logging
from app.schemas.workspace_schema import WorkspaceCredentials
from app.services.db_service import store_workspace

logger = logging.getLogger(__name__)


def process_oauth_success(oauth_data: dict) -> WorkspaceCredentials:
    """
    Process successful OAuth response from Slack.
    
    Args:
        oauth_data: OAuth response data from Slack API
        
    Returns:
        WorkspaceCredentials object
        
    Raises:
        ValueError: If OAuth response is missing required fields
    """
    if not oauth_data.get("ok"):
        error_msg = oauth_data.get("error", "Unknown error")
        logger.error(f"Slack OAuth error: {error_msg}")
        raise ValueError(error_msg)
    
    team_id = oauth_data["team"]["id"]
    access_token = oauth_data["access_token"]
    
    logger.info(f"OAuth successful for team: {team_id}")
    
    credentials = WorkspaceCredentials(team_id=team_id, access_token=access_token)
    store_workspace(credentials)
    
    return credentials
