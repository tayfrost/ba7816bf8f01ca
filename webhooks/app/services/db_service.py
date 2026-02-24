"""
Database Service

This service handles all database operations including:
- Storing user data
- Saving workspace credentials
- Managing message storage

NOTE: This service relies on the 'database' branch being implemented.
Once the database service is ready, this will become a gRPC client stub
to communicate with the database microservice.
"""

from app.schemas.message_schema import MessageEvent
from app.schemas.workspace_schema import WorkspaceCredentials


def store_in_db(message_event: MessageEvent):
    """
    Store message/event data in the database.
    
    Args:
        message_event: MessageEvent schema containing message metadata and content
    
    TODO: Implement gRPC client stub to database service
    """
    pass


def store_workspace(credentials: WorkspaceCredentials):
    """
    Store workspace credentials (team ID and access token) in the database.
    
    Args:
        credentials: WorkspaceCredentials schema with team_id and access_token
    
    TODO: Implement gRPC client stub to database service
    """
    pass
