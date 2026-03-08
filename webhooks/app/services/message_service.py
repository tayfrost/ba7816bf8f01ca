"""
Message Service

Handles message event processing for all providers (Slack, Gmail).
Applies filtering logic and stores approved messages via DB stub.
"""

import os
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

from app.schemas.message_schema import MessageEvent
from app.services.filter_service import filter_message
from app.services import db_stub as db

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]


# ── Slack ─────────────────────────────────────────────────────────

def process_slack_message(payload: dict, timestamp: str) -> bool:
    """
    Process a Slack message event.
    Extracts message data, filters, and stores if approved.
    Returns True if stored, False otherwise.
    """
    event = payload.get("event", {})

    if payload.get("type") != "event_callback" or event.get("type") != "message":
        return False

    # Ignore bot messages to avoid loops
    if event.get("subtype") == "bot_message":
        return False

    team_id = payload.get("team_id", "")
    user_id = event.get("user", "")
    text = event.get("text", "")
    message_ts = event.get("ts", timestamp)
    channel_id = event.get("channel", "")

    logger.info(f"Processing Slack message from team={team_id} user={user_id}")

    if not filter_message(text):
        return False

    # Ensure slack user exists before storing incident
    db.upsert_slack_user(
        team_id=team_id,
        slack_user_id=user_id,
        name="unknown",    # TODO: fetch from Slack API once user lookup is wired up
        surname="unknown",
    )

    workspace = db.get_workspace_by_team_id(team_id)

    db.create_flagged_incident(
        company_id=workspace.company_id,
        team_id=team_id,
        slack_user_id=user_id,
        message_ts=message_ts,
        channel_id=channel_id,
        raw_message_text={"text": text},
    )

    logger.info(f"Slack incident stored: team={team_id} user={user_id}")
    return True


# ── Gmail ─────────────────────────────────────────────────────────

def process_gmail_event(payload: dict) -> bool:
    """
    Process an incoming Gmail Pub/Sub notification.
    Decodes the notification, fetches new messages via History API,
    filters each one, and stores approved messages.
    Returns True if at least one message was stored, False otherwise.
    """
    try:
        msg_data = payload["message"]["data"]
        event = json.loads(base64.b64decode(msg_data).decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub payload: {e}")
        return False

    user_email = event.get("emailAddress")
    notif_history_id = str(event.get("historyId", ""))

    if not user_email:
        logger.warning("Pub/Sub notification missing emailAddress")
        return False

    account = db.get_gmail_account_by_email(user_email)
    if not account:
        logger.warning(f"No Gmail account found for: {user_email}")
        return False

    # Guard: brand new account, watch just started, no history to fetch yet
    if not account.last_history_id:
        logger.info(f"First notification for {user_email}, storing baseline historyId")
        db.update_gmail_history_id(user_email, notif_history_id)
        return False

    # Fetch new messages from Gmail History API
    messages, latest_history_id = _fetch_new_messages(account, user_email)

    # Always update history cursor even if no messages passed filter
    db.update_gmail_history_id(user_email, latest_history_id)

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

        db.create_flagged_incident(
            company_id=account.company_id,
            team_id=None,           # no slack team for gmail — revisit with Employee table
            slack_user_id=None,     # no slack user for gmail — revisit with Employee table
            message_ts=message.get("internalDate", ""),
            channel_id="gmail",
            raw_message_text={
                "text": body,
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
            },
        )
        stored += 1
        logger.info(f"Gmail incident stored for {user_email}: {headers.get('Subject', '')}")

    return stored > 0


# ── Gmail internals ───────────────────────────────────────────────

def _fetch_new_messages(account, user_email: str) -> Tuple[list, str]:
    """
    Calls Gmail History API from account.last_history_id.
    Returns (messages, latest_history_id).
    If history window is expired (404), resets cursor and returns empty.
    """
    try:
        creds = Credentials.from_authorized_user_info(
            json.loads(account.token_json), SCOPES
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
                msg_id = added["message"]["id"]
                full_msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="full"
                ).execute()
                messages.append(full_msg)

        return messages, latest_history_id

    except HttpError as e:
        # History window expired — reset cursor to current profile historyId
        if getattr(e, "resp", None) and e.resp.status == 404:
            logger.warning(f"History window expired for {user_email}, resetting cursor")
            profile = service.users().getProfile(userId="me").execute()
            return [], str(profile.get("historyId"))
        raise


def _extract_best_body(message: dict) -> Tuple[str, str]:
    """
    Walks the message payload to find the best text body.
    Prefers text/plain over text/html.
    Returns (body_text, mime_type).
    """
    payload = message.get("payload") or {}

    # Direct body on the top-level payload
    mime = payload.get("mimeType", "")
    data = (payload.get("body") or {}).get("data")
    if data and mime in ("text/plain", "text/html"):
        body = _b64url_decode(data)
        if mime == "text/html":
            body = _strip_html(body)
        return body, mime

    # Walk multipart
    plain_candidate: Optional[str] = None
    html_candidate: Optional[str] = None

    stack = [payload]
    while stack:
        node = stack.pop()
        mt = node.get("mimeType", "")
        pdata = (node.get("body") or {}).get("data")
        if pdata:
            decoded = _b64url_decode(pdata)
            if mt == "text/plain" and not plain_candidate:
                plain_candidate = decoded
            elif mt == "text/html" and not html_candidate:
                html_candidate = _strip_html(decoded)
        for part in node.get("parts", []) or []:
            stack.append(part)

    if plain_candidate:
        return plain_candidate, "text/plain"
    if html_candidate:
        return html_candidate, "text/html"
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