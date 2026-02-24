"""
Slack Controller

Handles Slack-related endpoints including OAuth callbacks and event webhooks.
"""

import json
import logging
import os
import httpx
from fastapi import APIRouter, Request, HTTPException

from app.services.slack_service import verify_slack_signature
from app.services.db_service import store_in_db, store_workspace
from app.services.filter_service import filter_message
from app.schemas.workspace_schema import WorkspaceCredentials
from app.schemas.message_schema import MessageEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


@router.get("/oauth/callback")
async def slack_oauth_callback(code: str = None, state: str = None):
    if not code:
        logger.warning("OAuth callback missing code parameter")
        raise HTTPException(status_code=400, detail="Missing code parameter")
    
    client_id = os.environ.get("SLACK_CLIENT_ID")
    client_secret = os.environ.get("SLACK_CLIENT_SECRET")
    redirect_uri = os.environ.get("SLACK_REDIRECT_URI")
    
    logger.info("OAuth callback received, exchanging code for token")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        data = response.json()
    
    if not data.get("ok"):
        error_msg = data.get("error", "Unknown error")
        logger.error(f"Slack OAuth error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    team_id = data["team"]["id"]
    access_token = data["access_token"]
    
    logger.info(f"OAuth successful for team: {team_id}")
    
    credentials = WorkspaceCredentials(team_id=team_id, access_token=access_token)
    store_workspace(credentials)
    
    return {"ok": True}


@router.post("/events")
async def slack_events(request: Request):
    body = await request.body()
    headers = request.headers
    payload = json.loads(body)
    
    if payload.get("type") == "url_verification":
        logger.info("URL verification request")
        return {"challenge": payload.get("challenge")}
    
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        logger.warning("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    if payload.get("type") == "event_callback" and payload.get("event", {}).get("type") == "message":
        team_id = payload.get("team_id", "")
        user_id = payload["event"].get("user", "")
        text = payload["event"].get("text", "")
        logger.info(f"Processing message from team {team_id}: {text}")
        
        if filter_message(text):
            message_event = MessageEvent(
                team_id=team_id,
                user_id=user_id,
                text=text,
                timestamp=timestamp
            )
            store_in_db(message_event)
    
    return {"ok": True}
