"""
Message Service
Handles message event processing for all providers (Slack, Gmail).
When gmail is connected to slack, replace syntehtic email with real email
"""

import json
import base64
import logging
import re
from typing import Optional, Tuple
from datetime import datetime, timezone
 
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
 
from app.services.filter_service import filter_message
from app.services import db_service as db

from backend.New_database import new_oop as model
from backend.New_database.new_crud import Session
from sqlalchemy import select
 
logger = logging.getLogger(__name__)
 
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]
 
 
# ── Slack ─────────────────────────────────────────────────────────
 
def process_slack_message(payload: dict, timestamp: str) -> bool:
    """
    Process a Slack event_callback message event.
    Filters and stores the message if it crosses the risk threshold.
    Returns True if stored, False otherwise.
    """
    event = payload.get("event", {})
 
    if payload.get("type") != "event_callback" or event.get("type") != "message":
        return False
 
    if event.get("subtype") == "bot_message":
        return False
 
    team_id    = payload.get("team_id", "")
    slack_uid  = event.get("user", "")
    text       = event.get("text", "")
    message_ts = event.get("ts", timestamp)
    channel_id = event.get("channel", "")
 
    logger.info(f"Processing Slack message team={team_id} user={slack_uid}")
 
    if not filter_message(text):
        return False
 
    workspace = db.get_workspace_by_team_id(team_id)
    if not workspace:
        logger.warning(f"No active workspace for team_id={team_id}")
        return False
 
    company_id: int = workspace.company_id
 
    existing_account = db.get_slack_account(team_id, slack_uid)
    if existing_account:
        user_id = existing_account.user_id
    else:
        user     = db.create_viewer_seat(company_id, display_name=f"Slack user {slack_uid}")
        user_id  = user.user_id
        db.create_slack_account(company_id, team_id, slack_uid, user_id)
        logger.info(f"New viewer seat + slack_account created for {slack_uid} team={team_id}")
 
    try:
        sent_at = datetime.fromtimestamp(float(message_ts), tz=timezone.utc)
    except (ValueError, TypeError):
        sent_at = datetime.now(tz=timezone.utc)
 
    incident = db.create_message_incident(
        company_id,
        user_id,
        source="slack",
        sent_at=sent_at,
        content_raw={"text": text},
        conversation_id=channel_id,
    )
 
    logger.info(f"Slack incident stored id={incident.message_id} team={team_id} user={slack_uid}")
    return True
 
 
# ── Gmail ─────────────────────────────────────────────────────────
 
def process_gmail_event(payload: dict) -> bool:
    """
    Process an incoming Gmail Pub/Sub notification.
    Decodes the notification, fetches new messages via the History API,
    filters each one, and stores any that pass.
    Returns True if at least one message was stored.
    """
    try:
        msg_data = payload["message"]["data"]
        event    = json.loads(base64.b64decode(msg_data).decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub payload: {e}")
        return False
 
    user_email       = event.get("emailAddress")
    notif_history_id = str(event.get("historyId", ""))
 
    if not user_email:
        logger.warning("Pub/Sub notification missing emailAddress")
        return False
 
    account = _get_mailbox_by_email_any_company(user_email)
    if not account:
        logger.warning(f"No google_mailboxes row for {user_email}")
        return False
 
    if not account.last_history_id:
        logger.info(f"First notification for {user_email}, storing baseline historyId")
        db.set_google_mailbox_history_id(account.google_mailbox_id, notif_history_id)
        return False
 
    messages, latest_history_id = _fetch_new_messages(account, user_email)
 
    db.set_google_mailbox_history_id(account.google_mailbox_id, latest_history_id)
 
    stored = 0
    for message in messages:
        body, _ = _extract_best_body(message)
        if not body:
            continue
 
        if not filter_message(body):
            continue
 
        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }
 
        raw_ts = message.get("internalDate", "")
        try:
            sent_at = datetime.fromtimestamp(int(raw_ts) / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            sent_at = datetime.now(tz=timezone.utc)
 
        incident = db.create_message_incident(
            account.company_id,
            account.user_id,
            source="gmail",
            sent_at=sent_at,
            content_raw={
                "text":    body,
                "subject": headers.get("Subject", ""),
                "from":    headers.get("From", ""),
                "to":      headers.get("To", ""),
            },
            conversation_id="gmail",
        )
        stored += 1
        logger.info(
            f"Gmail incident stored id={incident.message_id} {user_email} "
            f"subject={headers.get('Subject', '')!r}"
        )
 
    return stored > 0
 
 
def _get_mailbox_by_email_any_company(email_address: str):

    session = Session()
    try:
        return session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()
    finally:
        session.close()
 
 
# ── Gmail internals ───────────────────────────────────────────────
 
def _fetch_new_messages(account, user_email: str) -> Tuple[list, str]:
    """
    Call the Gmail History API from account.last_history_id.
    The refresh token inside account.token_json is used to obtain a fresh
    access token automatically — it is never stored separately.
    Returns (messages, latest_history_id).
    Resets the cursor on a 404 (expired history window).
    """
    try:
        creds = Credentials.from_authorized_user_info(
            json.loads(account.token_json) if isinstance(account.token_json, str)
            else account.token_json,
            GMAIL_SCOPES,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
 
        service = build("gmail", "v1", credentials=creds)
 
        hist = service.users().history().list(
            userId="me",
            startHistoryId=account.last_history_id,
            historyTypes=["messageAdded"],
        ).execute()
 
        latest_history_id = str(hist.get("historyId") or account.last_history_id)
 
        messages = []
        for h in hist.get("history", []):
            for added in h.get("messagesAdded", []):
                msg_id   = added["message"]["id"]
                full_msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
                messages.append(full_msg)
 
        return messages, latest_history_id
 
    except HttpError as e:
        if getattr(e, "resp", None) and e.resp.status == 404:
            logger.warning(f"History window expired for {user_email}, resetting cursor")
            profile = service.users().getProfile(userId="me").execute()
            return [], str(profile.get("historyId"))
        raise
 
 
def _extract_best_body(message: dict) -> Tuple[str, str]:
    """
    Walk the message payload tree to find the best text body.
    Prefers text/plain; falls back to stripped text/html.
    """
    payload = message.get("payload") or {}
 
    mime = payload.get("mimeType", "")
    data = (payload.get("body") or {}).get("data")
    if data and mime in ("text/plain", "text/html"):
        body = _b64url_decode(data)
        return (_strip_html(body) if mime == "text/html" else body), mime
 
    plain: Optional[str] = None
    html:  Optional[str] = None
 
    stack = [payload]
    while stack:
        node  = stack.pop()
        mt    = node.get("mimeType", "")
        pdata = (node.get("body") or {}).get("data")
        if pdata:
            decoded = _b64url_decode(pdata)
            if mt == "text/plain" and not plain:
                plain = decoded
            elif mt == "text/html" and not html:
                html = _strip_html(decoded)
        for part in node.get("parts", []) or []:
            stack.append(part)
 
    if plain:
        return plain, "text/plain"
    if html:
        return html, "text/html"
    return "", ""
 
 
def _b64url_decode(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(
        (data + padding).encode("utf-8")
    ).decode("utf-8", errors="replace")
 
 
def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()