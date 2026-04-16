"""
Handles OAuth flow business logic including processing OAuth responses and storing workspace credentials.
"""

import os
import json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, quote

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from app.schemas.workspace_schema import WorkspaceCredentials
#from app.services import db_stub as db
from app.services import db_service as db

logger = logging.getLogger(__name__)

GMAIL_CLIENT_ID     = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_PUBSUB_TOPIC  = os.getenv("GMAIL_PUBSUB_TOPIC")
BASE_URL            = os.getenv("BASE_URL")

SLACK_CLIENT_ID     = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI  = os.getenv("SLACK_REDIRECT_URI")

SLACK_SCOPES = "app_mentions:read,channels:history,channels:read,chat:write,groups:history,users:read,users:read.email"
 
GMAIL_REDIRECT_URI  = f"{BASE_URL}/gmail/oauth/callback" if BASE_URL else None
 
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    #"https://www.googleapis.com/auth/pubsub",
]

GMAIL_PUBSUB_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC")

def get_slack_auth_url(company_id: int) -> str:
    """
    Build the full Slack OAuth URL with all required parameters.
    company_id is encoded as state so it survives the round trip.
    """
    if not SLACK_CLIENT_ID or not SLACK_REDIRECT_URI:
        raise RuntimeError("Missing env vars: SLACK_CLIENT_ID / SLACK_REDIRECT_URI")
    params = {
        "client_id":    SLACK_CLIENT_ID,
        "scope":        SLACK_SCOPES,
        "redirect_uri": SLACK_REDIRECT_URI,
        "state":        str(company_id),
    }
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


def process_slack_oauth(oauth_data: dict) -> WorkspaceCredentials:
    if not oauth_data.get("ok"):
        error_msg = oauth_data.get("error", "Unknown error")
        logger.error(f"Slack OAuth error: {error_msg}")
        raise ValueError(error_msg)
 
    team_id      = oauth_data["team"]["id"]
    access_token = oauth_data["access_token"]
    company_id   = int(oauth_data.get("_company_id") or 0)
 
    if not company_id:
        raise ValueError("company_id missing — cannot associate workspace with a tenant")
 
    existing = db.get_workspace_by_team_id(team_id)
    if existing:
        db.update_workspace_token(team_id, access_token)
        logger.info(f"Slack workspace token refreshed team={team_id}")
    else:
        db.create_workspace(company_id, team_id, access_token)
        logger.info(f"Slack workspace created team={team_id} company={company_id}")
    credentials = WorkspaceCredentials(team_id=team_id, access_token=access_token)
    return credentials



def _build_flow() -> Flow:
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET or not GMAIL_REDIRECT_URI:
        raise RuntimeError(
            "Missing env vars: GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / BASE_URL"
        )
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id":     GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
                "redirect_uris": [GMAIL_REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
    )
    flow.redirect_uri = GMAIL_REDIRECT_URI
    return flow

"""
def get_gmail_auth_url(company_id: int) -> str:
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=str(company_id),
    )
    return auth_url
"""

def get_gmail_auth_url(company_id: int, return_page: str = "connect-accounts") -> str:
    """
    Returns the Google consent URL with company_id and return_page encoded in state.
    State format: "{company_id}:{return_page}" — callback decodes both.
    Called by the gmail_controller login route.
    """
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=f"{company_id}:{return_page}",
    )
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
   # 1. Exchange code → credentials
    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier="")
    creds = flow.credentials
 
    # 2. Get employee's Gmail address
    service    = build("gmail", "v1", credentials=creds)
    profile    = service.users().getProfile(userId="me").execute()
    user_email = profile["emailAddress"]
 
    logger.info(f"Gmail OAuth completed for {user_email} company={company_id}")
 
    # 3. Upsert mailbox
    global_mailbox = db.get_mailbox_by_email_global(user_email)
    if global_mailbox and global_mailbox.company_id != company_id:
        raise ValueError("EMAIL_ALREADY_REGISTERED")

    existing_mailbox = db.get_google_mailbox_by_email(company_id, user_email)
    if existing_mailbox:
        # Reconnect — refresh the token, keep the existing user_id
        mailbox = db.update_google_mailbox_token(
            existing_mailbox.google_mailbox_id,
            creds.to_json(),
        )
        logger.info(f"Gmail token refreshed for {user_email}")
    else:
        # First connect — try to link with an existing Slack account by email
        # so we don't create a duplicate User row for someone already on Slack.
        slack_acct = db.get_slack_account_by_email(company_id, user_email)
        if slack_acct:
            existing_user_id = (
                _uuid.UUID(slack_acct.user_id)
                if isinstance(slack_acct.user_id, str)
                else slack_acct.user_id
            )
            mailbox = db.create_google_mailbox(
                company_id,
                existing_user_id,
                user_email,
                creds.to_json(),
            )
            logger.info(
                f"Gmail mailbox linked to existing Slack user "
                f"{user_email} user_id={existing_user_id}"
            )
        else:
            # No Slack account found — create a fresh viewer seat
            user = db.create_viewer_seat(company_id, display_name=user_email)
            mailbox = db.create_google_mailbox(
                company_id,
                user.user_id,
                user_email,
                creds.to_json(),
            )
            logger.info(f"Gmail mailbox created for {user_email} user_id={user.user_id}")
 
    # 4. Start Gmail Pub/Sub watch
    resp = service.users().watch(
        userId="me",
        body={"labelIds": ["INBOX", "SENT"], "topicName": GMAIL_PUBSUB_TOPIC},
    ).execute()
 
    # 5. Persist historyId and watch expiry using the mailbox PK
    watch_expiration = datetime.fromtimestamp(
        int(resp["expiration"]) / 1000, tz=timezone.utc
    )
    db.set_google_mailbox_history_id(
        mailbox.google_mailbox_id, str(resp["historyId"])
    )
    db.update_google_mailbox_watch_expiration(
        mailbox.google_mailbox_id, watch_expiration
    )
 
    logger.info(f"Gmail watch started for {user_email} expires={watch_expiration}")
    return user_email
