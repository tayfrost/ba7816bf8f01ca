# app/controllers/gmail_controller.py
"""
Gmail Controller

Handles Gmail-related endpoints including OAuth login/callback
and incoming Pub/Sub event webhooks.
Controllers handle HTTP request/response concerns and delegate
business logic to services.
"""

import asyncio
import logging
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from app.services.gmail_service import verify_gmail_token
from app.services.oauth_service import get_gmail_auth_url, process_gmail_oauth
from app.services.message_service import process_gmail_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/oauth/login")
def gmail_login(company_id: int, return_page: str = "connect-accounts"):
    """
    Redirects the user to Google's consent screen.
    company_id and return_page are encoded into the OAuth state so they
    survive the round trip and are available in the callback.

    Frontend connect button should hit:
      GET /gmail/oauth/login?company_id=<id>
      GET /gmail/oauth/login?company_id=<id>&return_page=register-gmail
    """
    if not company_id:
        raise HTTPException(status_code=400, detail="Missing company_id")
    return RedirectResponse(get_gmail_auth_url(company_id, return_page=return_page))


@router.get("/oauth/callback")
def gmail_callback(code: str = None, state: str = None):
    """
    Google redirects here after the user approves consent.
    Exchanges the code for credentials, stores them, and
    immediately starts the Gmail watch (Pub/Sub subscription).

    State format: "{company_id}:{return_page}" (new) or "{company_id}" (legacy).
    """
    if not code:
        logger.warning("Gmail OAuth callback missing code parameter")
        raise HTTPException(status_code=400, detail="Missing code parameter")

    if not state:
        logger.warning("Gmail OAuth callback missing state parameter")
        raise HTTPException(status_code=400, detail="Missing company_id in state")

    # Decode state — supports new "42:register-gmail" and legacy "42" formats
    if ":" in state:
        raw_id, return_page = state.split(":", 1)
    else:
        raw_id, return_page = state, "connect-accounts"

    try:
        company_id = int(raw_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company_id in state")

    frontend_url = os.environ.get("FRONTEND_URL", "https://sentinelai.work")
    try:
        user_email = process_gmail_oauth(code, company_id)
        logger.info(f"Gmail connected successfully: {user_email} company={company_id} return={return_page}")
        return RedirectResponse(
            f"{frontend_url}/{return_page}?provider=gmail&status=success",
            status_code=302,
        )
    except RuntimeError as e:
        logger.error(f"Gmail OAuth failed: {e}")
        return RedirectResponse(
            f"{frontend_url}/{return_page}?provider=gmail&status=error",
            status_code=302,
        )


@router.post("/events")
async def gmail_events(request: Request):
    """
    Receives Pub/Sub push notifications from Google Cloud.
    Verifies the OIDC Bearer token, then fetches and processes
    any new messages via the Gmail History API.

    Note: must return 200 quickly — Pub/Sub will retry on failure.
    """
    verify_gmail_token(request)

    payload = await request.json()
    stored = await asyncio.to_thread(process_gmail_event, payload)

    return {"ok": True, "stored": stored}