# app/controllers/slack_controller.py
"""
Slack Controller

Handles Slack-related endpoints including OAuth callbacks and event webhooks.
Controllers handle HTTP request/response concerns and delegate business logic to services.
"""

import json
import logging
import os
import httpx
from fastapi import APIRouter, Request, HTTPException

from app.services.slack_service import verify_slack_signature
from app.services.oauth_service import process_slack_oauth
from app.services.message_service import process_slack_message

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
                "redirect_uri": redirect_uri,
            }
        )
        data = response.json()

    try:
        process_slack_oauth(data)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events")
async def slack_events(request: Request):
    body = await request.body()
    headers = request.headers
    payload = json.loads(body)

    if payload.get("type") == "url_verification":
        logger.info("URL verification request")
        return {"challenge": payload.get("challenge")}

    if headers.get("X-Slack-Retry-Num"):
        logger.info(f"Dropping Slack retry #{headers['X-Slack-Retry-Num']}")
        return {"ok": True}

    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(body, timestamp, signature):
        logger.warning("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    process_slack_message(payload, timestamp)

    return {"ok": True}