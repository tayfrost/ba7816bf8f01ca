"""
Message Service

Handles message event processing including extraction, filtering, and storage.
This service can be extended with a factory pattern for different message types.
"""

import logging
from app.schemas.message_schema import MessageEvent
from app.services.filter_service import filter_message
from app.services.db_service import store_in_db

logger = logging.getLogger(__name__)


def process_message_event(payload: dict, timestamp: str) -> bool:
    """
    Process a message event from Slack.
    
    Extracts message data, applies filtering logic, and stores approved messages.
    Can be extended with factory pattern for different event types.
    
    Args:
        payload: Event payload from Slack
        timestamp: Request timestamp from headers
        
    Returns:
        True if message was processed and stored, False otherwise
    """
    event = payload.get("event", {})
    
    if payload.get("type") != "event_callback" or event.get("type") != "message":
        return False
    
    team_id = payload.get("team_id", "")
    user_id = event.get("user", "")
    text = event.get("text", "")
    
    logger.info(f"Processing message from team {team_id}: {text}")
    
    if filter_message(text):
        message_event = MessageEvent(
            team_id=team_id,
            user_id=user_id,
            text=text,
            timestamp=timestamp
        )
        store_in_db(message_event)
        return True
    
    return False
