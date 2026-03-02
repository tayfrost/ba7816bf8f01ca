"""
OAuth Service

Handles OAuth flow business logic including processing OAuth responses
and storing workspace credentials.
"""

import os
import json
import logging
from datetime import datetime, timezone

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from app.schemas.workspace_schema import WorkspaceCredentials
from app.services import db_stub as db

logger = logging.getLogger(__name__)

GMAIL_PUBSUB_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC")

def process_slack_oauth(oauth_data: dict) -> WorkspaceCredentials:
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
    #store_workspace(credentials)
    
    return credentials


# ── Gmail config ─────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL")
REDIRECT_URI = f"{BASE_URL}/gmail/oauth/callback" if BASE_URL else None
GMAIL_PUBSUB_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC")


# ── Gmail helpers ─────────────────────────────────────────────────

def _build_flow() -> Flow:
    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        raise RuntimeError(
            "Missing env vars: GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / BASE_URL"
        )
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    return flow


def get_gmail_auth_url(company_id: int) -> str:
   
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=str(company_id),
    )
    return auth_url

def get_gmail_auth_url(company_id: int) -> str:
    """
    Returns the Google consent URL with company_id encoded in state.
    Called by the gmail_controller login route.
    """
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=str(company_id),
    )
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("code_challenge", None)
    params.pop("code_challenge_method", None)
    clean_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=clean_query))


def process_gmail_oauth(code: str, company_id: int) -> str:
    """
    Full Gmail OAuth completion flow:
      1. Exchange code for credentials
      2. Fetch the Gmail address to use as identifier
      3. Store credentials in DB
      4. Start Gmail watch (Pub/Sub subscription)
      5. Store historyId + watch expiration in DB
    Returns user_email.
    """
    # 1. Exchange code for credentials
    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier="")
    #flow.fetch_token(code=code)
    creds = flow.credentials

    # 2. Identify the Gmail account
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    user_email = profile["emailAddress"]

    logger.info(f"Gmail OAuth successful for: {user_email} company={company_id}")

    # 3. Store credentials
    db.create_gmail_account(company_id, user_email, creds.to_json())

    # 4. Start Gmail watch
    resp = service.users().watch(
        userId="me",
        body={"labelIds": ["INBOX", "SENT"], "topicName": GMAIL_PUBSUB_TOPIC}
    ).execute()

    # 5. Convert expiration to datetime and store alongside historyId
    watch_expiration = datetime.fromtimestamp(
        int(resp["expiration"]) / 1000, tz=timezone.utc
    )
    db.update_gmail_watch(user_email, str(resp["historyId"]), watch_expiration)

    logger.info(f"Gmail watch started for: {user_email} expires={watch_expiration}")

    return user_email