"""
Message Service
Handles Slack and Gmail webhook events.

Responsibilities:
  1. Decode the incoming event.
  2. Resolve or register the canonical user (create viewer seat if new).
  3. Fire-and-forget dispatch to filter service via gRPC.
     The filter service callback handles AI dispatch if a risk is detected.
"""

import json
import base64
import logging
import re
import uuid
from typing import Optional, Tuple
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.filter_service import dispatch_to_filter
from app.services.slack_user_service import lookup_slack_user
from app.services import db_service as db

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


# ── Slack ─────────────────────────────────────────────────────────

def process_slack_message(payload: dict, timestamp: str) -> bool:
    """
    Process a Slack event_callback message event.
    Resolves the user, then fires-and-forgets to the filter service.
    The filter callback dispatches to AI if a risk is detected.
    Returns True if dispatched to filter, False otherwise.
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

    workspace = db.get_workspace_by_team_id(team_id)
    if not workspace:
        logger.warning(f"No active workspace for team_id={team_id}")
        return False

    company_id: int = workspace.company_id

    first_name, last_name, email = lookup_slack_user(workspace.access_token, slack_uid)
    display_name = (
        f"{first_name} {last_name}".strip()
        if first_name != "unknown" else f"Slack user {slack_uid}"
    )
    logger.info(f"Slack user lookup: {slack_uid} -> {display_name} email={email}")

    existing_account = db.get_slack_account(team_id, slack_uid)
    if existing_account:
        user_id = existing_account.user_id

        # ── Eventually-consistent merge: backfill email and check for duplicate user ──
        if email and not existing_account.email:
            db.update_slack_account_email(team_id, slack_uid, email)
            logger.info(f"Backfilled email for {slack_uid}: {email}")

            # If a Gmail mailbox with this email already exists for a DIFFERENT user
            # in the same company, the two records represent the same person → merge.
            mailbox = db.get_mailbox_by_email_global(email)
            if (
                mailbox
                and str(mailbox.user_id) != str(user_id)
                and mailbox.company_id == company_id
            ):
                keep_uid = str(mailbox.user_id)
                drop_uid = str(user_id)
                logger.info(
                    f"[merge] Email backfill revealed duplicate users: "
                    f"keeping Gmail user {keep_uid}, merging Slack user {drop_uid}"
                )
                try:
                    db.merge_users(company_id, keep_uid=keep_uid, drop_uid=drop_uid)
                    user_id = uuid.UUID(keep_uid)
                except Exception as exc:
                    logger.error(f"[merge] merge_users failed (non-fatal): {exc}")
    else:
        # New Slack user — create a temporary seat, then create the account.
        # create_slack_account internally calls find_user_id_by_email and may
        # override the user_id we pass with an existing Gmail user's id.
        # If that happens the seat we just created becomes an orphan → delete it.
        temp_seat = db.create_viewer_seat(company_id, display_name=display_name)
        temp_uid  = temp_seat.user_id
        acct      = db.create_slack_account(company_id, team_id, slack_uid, temp_uid, email=email)
        # Some test stubs (and older implementations) return None here.
        # Fall back to the temporary seat to keep processing resilient.
        if acct and getattr(acct, "user_id", None):
            user_id = uuid.UUID(str(acct.user_id))
        else:
            user_id = temp_uid

        if user_id != temp_uid and str(user_id) != str(temp_uid):
            # Linking resolved to an existing user — orphan the temp seat.
            logger.info(
                f"[merge] Slack account linked to existing user {user_id}; "
                f"deleting orphaned viewer seat {temp_uid}"
            )
            try:
                db.delete_user(company_id, temp_uid)
            except Exception as exc:
                logger.warning(f"[merge] Could not delete orphaned seat {temp_uid}: {exc}")
        else:
            logger.info(
                f"New viewer seat + slack_account created for {slack_uid} "
                f"team={team_id} email={email}"
            )

    try:
        sent_at = datetime.fromtimestamp(float(message_ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        sent_at = datetime.now(tz=timezone.utc).isoformat()

    dispatch_to_filter(
        meta={
            "user_id":         str(user_id),
            "company_id":      company_id,
            "source":          "slack",
            "sent_at":         sent_at,
            "conversation_id": channel_id,
            "team_id":         team_id,
            "slack_user_id":   slack_uid,
            "email":           email,
            "content_raw":     {"text": text},
        },
        text=text,
    )
    return True


# ── Gmail ─────────────────────────────────────────────────────────

def process_gmail_event(payload: dict) -> bool:
    """
    Process an incoming Gmail Pub/Sub notification.
    Fetches new messages via the History API and fire-and-forgets each
    to the filter service. The filter callback dispatches to AI if a risk
    is detected. Returns True if at least one message was dispatched to filter.
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

    dispatched = 0
    for message in messages:
        body, _ = _extract_best_body(message)
        if not body:
            continue

        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        raw_ts = message.get("internalDate", "")
        try:
            sent_at = datetime.fromtimestamp(int(raw_ts) / 1000, tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            sent_at = datetime.now(tz=timezone.utc).isoformat()

        dispatch_to_filter(
            meta={
                "user_id":         str(account.user_id),
                "company_id":      account.company_id,
                "source":          "gmail",
                "sent_at":         sent_at,
                "conversation_id": "gmail",
                "email":           user_email,
                "subject":         headers.get("Subject", ""),
                "from":            headers.get("From", ""),
                "to":              headers.get("To", ""),
                "content_raw": {
                    "text":    body,
                    "subject": headers.get("Subject", ""),
                    "from":    headers.get("From", ""),
                    "to":      headers.get("To", ""),
                },
            },
            text=body,
        )
        dispatched += 1

    if dispatched:
        logger.info(f"Gmail: dispatched {dispatched} message(s) to filter for {user_email}")
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