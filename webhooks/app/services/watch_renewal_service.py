"""
Gmail Pub/Sub watches expire roughly every 7 days. This service is called
by APScheduler on a daily schedule and renews any watch that is either:
  - Already expired (watch_expiration is in the past), or
  - Expiring within the next RENEWAL_THRESHOLD_HOURS hours
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services import db_service as db

logger = logging.getLogger(__name__)

GMAIL_PUBSUB_TOPIC= os.getenv("GMAIL_PUBSUB_TOPIC")
RENEWAL_THRESHOLD_HOURS  = int(os.getenv("GMAIL_WATCH_RENEWAL_THRESHOLD_HOURS", "24"))

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    #"https://www.googleapis.com/auth/pubsub",
]


def renew_expiring_watches() -> dict:

    threshold = datetime.now(tz=timezone.utc) + timedelta(hours=RENEWAL_THRESHOLD_HOURS)
    companies = db.list_companies()

    summary = {"checked": 0, "renewed": 0, "skipped": 0, "failed": 0}

    for company in companies:
        mailboxes = db.list_google_mailboxes_for_company(company.company_id)

        for mailbox in mailboxes:
            summary["checked"] += 1

            if not _needs_renewal(mailbox, threshold):
                summary["skipped"] += 1
                continue

            try:
                _renew_watch(mailbox)
                summary["renewed"] += 1
            except Exception as e:
                summary["failed"] += 1
                logger.error(
                    f"Failed to renew watch for mailbox_id={mailbox.google_mailbox_id} "
                    f"email={mailbox.email_address}: {e}"
                )

    logger.info(
        f"Watch renewal run complete: checked={summary['checked']} "
        f"renewed={summary['renewed']} skipped={summary['skipped']} "
        f"failed={summary['failed']}"
    )
    return summary


def _needs_renewal(mailbox, threshold: datetime) -> bool:
    if mailbox.watch_expiration is None:
        logger.warning(
            f"mailbox_id={mailbox.google_mailbox_id} has no watch_expiration — "
            f"scheduling for immediate renewal"
        )
        return True

    expiry = mailbox.watch_expiration
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return expiry <= threshold


def _renew_watch(mailbox) -> None:
    token_data = (
        json.loads(mailbox.token_json)
        if isinstance(mailbox.token_json, str)
        else mailbox.token_json
    )

    creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
        except RefreshError as e:
            raise RuntimeError(
                f"Token refresh failed for {mailbox.email_address} — "
                f"admin may need to reconnect: {e}"
            ) from e

        # Persist the refreshed token so it isn't re-fetched unnecessarily
        db.update_google_mailbox_token(
            mailbox.google_mailbox_id, json.loads(creds.to_json())
        )

    service = build("gmail", "v1", credentials=creds)

    try:
        resp = service.users().watch(
            userId="me",
            body={
                "labelIds": ["INBOX", "SENT"],
                "topicName": GMAIL_PUBSUB_TOPIC,
            },
        ).execute()
    except HttpError as e:
        raise RuntimeError(
            f"Gmail watch API error for {mailbox.email_address}: "
            f"status={e.resp.status} reason={e.reason}"
        ) from e

    watch_expiration = datetime.fromtimestamp(
        int(resp["expiration"]) / 1000, tz=timezone.utc
    )

    db.update_google_mailbox_watch_expiration(
        mailbox.google_mailbox_id, watch_expiration
    )
    db.set_google_mailbox_history_id(
        mailbox.google_mailbox_id, str(resp["historyId"])
    )

    logger.info(
        f"Watch renewed for {mailbox.email_address} "
        f"mailbox_id={mailbox.google_mailbox_id} "
        f"expires={watch_expiration}"
    )
