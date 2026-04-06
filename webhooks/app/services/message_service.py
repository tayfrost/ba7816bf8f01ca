"""
Message Service
Handles Slack and Gmail webhook events.

Responsibilities:
  1. Decode the incoming event.
  2. Resolve or register the canonical user (create viewer seat if new).
  3. Send message to filter service synchronously.
  4. If filter deems it a risk, dispatch to AI service.
"""

import json
import base64
import logging
import re
from typing import Optional, Tuple
from datetime import datetime, timezone
import os
import requests

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.filter_service import filter_message, filter_messages, FilterResult
from app.services.slack_user_service import lookup_slack_user
from app.services import db_service as db

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_service:8001/analyze")


# ── Send to AI Service ────────────────────────────────────────────────────────

def _dispatch_to_ai(payload: dict) -> None:
    """Send a risk-flagged message to the AI service for analysis."""
    try:
        logger.info(f"Dispatching incident to AI Service: {AI_SERVICE_URL}")
        response = requests.post(AI_SERVICE_URL, json=payload, timeout=60)
        response.raise_for_status()
        logger.info("AI Service successfully processed the incident.")
    except Exception as e:
        logger.error(f"Failed to dispatch to AI Service: {e}")


# ── Slack ─────────────────────────────────────────────────────────

def process_slack_message(payload: dict, timestamp: str) -> bool:
    """
    Process a Slack event_callback message event.
    Filters the message; if risk, dispatches to AI service.
    Returns True if dispatched, False otherwise.
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

    result = filter_message(text)
    if not result or not result.is_risk:
        return False

    logger.info(f"Filter response: category={result.category}, is_risk={result.is_risk}, confidence={result.category_confidence:.3f}")

    workspace = db.get_workspace_by_team_id(team_id)
    if not workspace:
        logger.warning(f"No active workspace for team_id={team_id}")
        return False

    company_id: int = workspace.company_id

    first_name, last_name, email = lookup_slack_user(
        workspace.access_token, slack_uid
    )
    display_name = (
        f"{first_name} {last_name}".strip()
        if first_name != "unknown" else f"Slack user {slack_uid}"
    )
    logger.info(f"Slack user lookup: {slack_uid} -> {display_name} email={email}")

    existing_account = db.get_slack_account(team_id, slack_uid)
    if existing_account:
        user_id = existing_account.user_id
        if email and not existing_account.email:
            db.update_slack_account_email(team_id, slack_uid, email)
            logger.info(f"Backfilled email for {slack_uid}: {email}")
    else:
        user    = db.create_viewer_seat(company_id, display_name=display_name)
        user_id = user.user_id
        db.create_slack_account(company_id, team_id, slack_uid, user_id, email=email)
        logger.info(f"New viewer seat + slack_account created for {slack_uid} team={team_id} email={email}")

    try:
        sent_at = datetime.fromtimestamp(float(message_ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        sent_at = datetime.now(tz=timezone.utc).isoformat()

    _dispatch_to_ai({
        "message":          text,
        "filter_category":  result.category,
        "filter_severity":  result.severity,
        "company_id":       company_id,
        "user_id":          str(user_id),
        "source":           "slack",
        "sent_at":          sent_at,
        "conversation_id":  channel_id,
        "content_raw":      {"text": text},
    })
    return True


# ── Gmail ─────────────────────────────────────────────────────────

def process_gmail_event(payload: dict) -> bool:
    """
    Process an incoming Gmail Pub/Sub notification.
    Fetches new messages via the History API, batch-filters them,
    and dispatches any risks to the AI service.
    Returns True if at least one message was dispatched.
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

    account = db.get_mailbox_by_email_global(user_email)
    if not account:
        logger.warning(f"No google_mailboxes row for {user_email}")
        return False

    if not account.last_history_id:
        logger.info(f"First notification for {user_email}, storing baseline historyId")
        db.set_google_mailbox_history_id(account.google_mailbox_id, notif_history_id)
        return False

    messages, latest_history_id = _fetch_new_messages(account, user_email)
    db.set_google_mailbox_history_id(account.google_mailbox_id, latest_history_id)

    # Extract bodies first so we can batch-filter
    extracted = []
    for message in messages:
        body, _ = _extract_best_body(message)
        extracted.append((message, body))

    bodies      = [body for _, body in extracted if body]
    body_indices = [i for i, (_, body) in enumerate(extracted) if body]

    if not bodies:
        return False

    logger.info(f"Gmail: filtering {len(bodies)} message(s) for {user_email}")

    filter_results = filter_messages(bodies)

    dispatched = 0
    for filter_idx, extracted_idx in enumerate(body_indices):
        result = filter_results[filter_idx]
        if not result or not result.is_risk:
            continue

        logger.info(f"Filter response: category={result.category}, is_risk={result.is_risk}, confidence={result.category_confidence:.3f}")

        message, body = extracted[extracted_idx]
        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        raw_ts = message.get("internalDate", "")
        try:
            sent_at = datetime.fromtimestamp(int(raw_ts) / 1000, tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            sent_at = datetime.now(tz=timezone.utc).isoformat()

        _dispatch_to_ai({
            "message":         body,
            "filter_category": result.category,
            "filter_severity": result.severity,
            "company_id":      account.company_id,
            "user_id":         str(account.user_id),
            "source":          "gmail",
            "sent_at":         sent_at,
            "conversation_id": "gmail",
            "content_raw": {
                "text":    body,
                "subject": headers.get("Subject", ""),
                "from":    headers.get("From", ""),
                "to":      headers.get("To", ""),
            },
        })
        dispatched += 1

    if dispatched:
        logger.info(f"Gmail: dispatched {dispatched} message(s) to AI service for {user_email}")
    return dispatched > 0


# ── Gmail internals ───────────────────────────────────────────────

def _fetch_new_messages(account, user_email: str) -> Tuple[list, str]:
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