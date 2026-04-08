"""db_service.py — thin HTTP client wrapping the internal API.

All functions mirror the previous direct-CRUD interface so that
oauth_service.py and message_service.py require no call-site changes.

Reads INTERNAL_API_URL from the environment (default: http://api:8000).
"""
import os
import uuid
import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE = os.getenv("INTERNAL_API_URL", "http://api:8000")


# ── HTTP helpers ──────────────────────────────────────────────────

def _get(path: str, **params) -> dict | None:
    """GET with query params. Returns parsed JSON or None on 404."""
    r = httpx.get(
        f"{_BASE}{path}",
        params={k: v for k, v in params.items() if v is not None},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict, **params) -> dict:
    """POST JSON body. Raises RuntimeError on non-2xx."""
    r = httpx.post(
        f"{_BASE}{path}",
        json=body,
        params={k: v for k, v in params.items() if v is not None},
    )
    if not r.is_success:
        raise RuntimeError(f"Internal API {path} → {r.status_code}: {r.text}")
    return r.json()


def _patch(path: str, body: dict) -> dict | None:
    """PATCH JSON body. Returns None on 404, raises RuntimeError on other errors."""
    r = httpx.patch(f"{_BASE}{path}", json=body)
    if r.status_code == 404:
        return None
    if not r.is_success:
        raise RuntimeError(f"Internal API {path} → {r.status_code}: {r.text}")
    return r.json()


def _ns(d: dict | None) -> SimpleNamespace | None:
    """Convert a response dict to a SimpleNamespace for attribute access."""
    if d is None:
        return None
    return SimpleNamespace(**d)


# ── Users ─────────────────────────────────────────────────────────

def create_viewer_seat(company_id: int, display_name: str, **_) -> SimpleNamespace:
    data = _post("/internal/users/viewer-seat", {
        "company_id": company_id,
        "display_name": display_name,
    })
    return _ns(data)


def get_user_by_id(company_id: int, user_id: uuid.UUID, **_) -> Optional[SimpleNamespace]:
    return _ns(_get(f"/internal/users/{user_id}", company_id=company_id))


# ── Google Mailboxes ──────────────────────────────────────────────

def create_google_mailbox(
    company_id: int,
    user_id: uuid.UUID,
    email_address: str,
    token_json,
    **_,
) -> SimpleNamespace:
    data = _post("/internal/mailboxes", {
        "company_id": company_id,
        "user_id": str(user_id),
        "email_address": email_address,
        "token_json": token_json,
    })
    return _ns(data)


def get_google_mailbox_by_email(
    company_id: int,
    email_address: str,
    **_,
) -> Optional[SimpleNamespace]:
    return _ns(_get("/internal/mailboxes/by-email", email=email_address, company_id=company_id))


def update_google_mailbox_token(
    google_mailbox_id: int,
    token_json,
    **_,
) -> Optional[SimpleNamespace]:
    return _ns(_patch(f"/internal/mailboxes/{google_mailbox_id}/token", {"token_json": token_json}))


def set_google_mailbox_history_id(
    google_mailbox_id: int,
    last_history_id: str,
    **_,
) -> None:
    _patch(f"/internal/mailboxes/{google_mailbox_id}/history-id", {"last_history_id": last_history_id})


def update_google_mailbox_watch_expiration(
    google_mailbox_id: int,
    watch_expiration: datetime,
    **_,
) -> None:
    _patch(f"/internal/mailboxes/{google_mailbox_id}/watch-expiration", {
        "watch_expiration": watch_expiration.isoformat(),
    })


def list_google_mailboxes_for_company(company_id: int, **_) -> list[SimpleNamespace]:
    data = _get(f"/internal/mailboxes/company/{company_id}") or []
    return [_ns(m) for m in data]


def get_mailbox_by_email_global(email_address: str) -> Optional[SimpleNamespace]:
    """Look up a mailbox by email across all companies (no company_id filter)."""
    return _ns(_get("/internal/mailboxes/by-email-global", email=email_address))


# ── Companies ─────────────────────────────────────────────────────

def list_companies(**_) -> list[SimpleNamespace]:
    data = _get("/internal/companies") or []
    return [_ns(c) for c in data]


# ── Slack Workspaces ──────────────────────────────────────────────

def create_workspace(
    company_id: int,
    team_id: str,
    access_token: str,
    **_,
) -> SimpleNamespace:
    data = _post("/internal/slack/workspaces", {
        "company_id": company_id,
        "team_id": team_id,
        "access_token": access_token,
    })
    return _ns(data)


def get_workspace_by_team_id(team_id: str, **_) -> Optional[SimpleNamespace]:
    return _ns(_get(f"/internal/slack/workspace/{team_id}"))


def update_workspace_token(team_id: str, access_token: str, **_) -> Optional[SimpleNamespace]:
    return _ns(_patch(f"/internal/slack/workspaces/{team_id}/token", {"access_token": access_token}))


# ── Slack Accounts ────────────────────────────────────────────────

def create_slack_account(
    company_id: int,
    team_id: str,
    slack_user_id: str,
    user_id: uuid.UUID,
    email: Optional[str] = None,
    **_,
) -> SimpleNamespace:
    data = _post("/internal/slack/accounts", {
        "company_id": company_id,
        "team_id": team_id,
        "slack_user_id": slack_user_id,
        "user_id": str(user_id),
        "email": email,
    })
    return _ns(data)


def get_slack_account(team_id: str, slack_user_id: str, **_) -> Optional[SimpleNamespace]:
    return _ns(_get(f"/internal/slack/user/{team_id}/{slack_user_id}"))


def get_slack_account_by_email(
    company_id: int,
    email: str,
    **_,
) -> Optional[SimpleNamespace]:
    """Find a Slack account by email address within a company. Returns None if not found."""
    return _ns(_get("/internal/slack/accounts/by-email", email=email, company_id=company_id))


def update_slack_account_email(
    team_id: str,
    slack_user_id: str,
    email: Optional[str],
    **_,
) -> None:
    _patch(f"/internal/slack/accounts/{team_id}/{slack_user_id}/email", {"email": email})


