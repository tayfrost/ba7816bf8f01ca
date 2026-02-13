import json
import logging
import os
import httpx
from fastapi import FastAPI, Request, HTTPException

from app.services.slack_service import verify_slack_signature
from app.utils.message_utils import filter_message, store_in_db
from app.utils.workspace_utils import store_workspace

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/slack/oauth/callback")
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
    
    store_workspace(team_id, access_token)
    
    return {"ok": True}


@app.post("/slack/events")
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
        text = payload["event"].get("text", "")
        message_ts = payload["event"].get("ts", "")
        logger.info(f"Processing message: {text}")
        
        if filter_message(text):
            store_in_db(payload["event"])
    
    return {"ok": True}