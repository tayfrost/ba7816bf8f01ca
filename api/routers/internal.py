"""Internal endpoints for service-to-service calls. No JWT required."""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas.incident import MessageIncidentCreate, MessageIncidentRead
from api.schemas.slack import SlackAccountRead, SlackWorkspaceRead
from api.schemas.user import UserRead
from database.services import (
    companies_crud,
    crud_google_mailboxes,
    crud_incident_scores,
    crud_message_incidents,
    crud_slack_accounts,
    slack_workspaces_crud,
    users_crud,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user_by_id(user_id: uuid.UUID, company_id: int):
    user = await asyncio.to_thread(users_crud.get_user_by_id, company_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/mailboxes/by-email")
async def get_mailbox_by_email(email: str, company_id: int):
    mailbox = await asyncio.to_thread(
        crud_google_mailboxes.get_google_mailbox_by_email, company_id, email
    )
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return {
        "google_mailbox_id": mailbox.google_mailbox_id,
        "company_id": mailbox.company_id,
        "user_id": mailbox.user_id,
        "email_address": mailbox.email_address,
        "token_json": mailbox.token_json,
        "last_history_id": mailbox.last_history_id,
        "watch_expiration": mailbox.watch_expiration,
    }


@router.get("/mailboxes/company/{company_id}")
async def get_mailboxes_for_company(company_id: int):
    mailboxes = await asyncio.to_thread(
        crud_google_mailboxes.list_google_mailboxes_for_company, company_id
    )
    return [
        {
            "google_mailbox_id": m.google_mailbox_id,
            "company_id": m.company_id,
            "user_id": m.user_id,
            "email_address": m.email_address,
            "token_json": m.token_json,
            "last_history_id": m.last_history_id,
            "watch_expiration": m.watch_expiration,
        }
        for m in mailboxes
    ]


@router.get("/slack/workspace/{team_id}", response_model=SlackWorkspaceRead)
async def get_workspace_by_team_id(team_id: str):
    ws = await asyncio.to_thread(slack_workspaces_crud.get_slack_workspace_by_team_id, team_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/slack/user/{team_id}/{slack_user_id}", response_model=SlackAccountRead)
async def get_slack_user(team_id: str, slack_user_id: str):
    acct = await asyncio.to_thread(crud_slack_accounts.get_slack_account, team_id, slack_user_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Slack account not found")
    return acct


@router.post("/incidents", response_model=MessageIncidentRead, status_code=201)
async def create_incident_internal(body: MessageIncidentCreate, company_id: int):
    try:
        return await asyncio.to_thread(
            crud_message_incidents.create_message_incident,
            company_id,
            user_id=body.user_id,
            source=body.source,
            sent_at=body.sent_at,
            content_raw=body.content_raw,
            conversation_id=body.conversation_id,
            recommendation=body.recommendation,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


class LinkAccountRequest(BaseModel):
    source: str
    email: str
    team_id: str | None = None
    slack_user_id: str | None = None
    company_id: int | None = None
    user_id: uuid.UUID | None = None


@router.post("/link-account")
async def link_or_create_account(body: LinkAccountRequest):
    if body.source == "slack":
        if not body.team_id or not body.slack_user_id:
            raise HTTPException(status_code=400, detail="team_id and slack_user_id required for slack source")
        acct = await asyncio.to_thread(
            crud_slack_accounts.get_slack_account, body.team_id, body.slack_user_id
        )
        if not acct:
            raise HTTPException(status_code=404, detail="Slack account not found")
        return {
            "source": "slack",
            "slack_user_id": acct.slack_user_id,
            "team_id": acct.team_id,
            "email": acct.email,
            "status": "found",
        }
    elif body.source == "gmail":
        if not body.company_id:
            raise HTTPException(status_code=400, detail="company_id required for gmail source")
        mailbox = await asyncio.to_thread(
            crud_google_mailboxes.get_google_mailbox_by_email, body.company_id, body.email
        )
        if not mailbox:
            raise HTTPException(status_code=404, detail="Gmail mailbox not found")
        return {
            "source": "gmail",
            "email": mailbox.email_address,
            "google_mailbox_id": mailbox.google_mailbox_id,
            "status": "found",
        }
    else:
        raise HTTPException(status_code=400, detail="source must be 'slack' or 'gmail'")


# ── Users ─────────────────────────────────────────────────────────

class ViewerSeatRequest(BaseModel):
    company_id: int
    display_name: str | None = None


@router.post("/users/viewer-seat", response_model=UserRead, status_code=201)
async def create_viewer_seat(body: ViewerSeatRequest):
    try:
        user = await asyncio.to_thread(
            users_crud.create_user,
            body.company_id,
            role="viewer",
            status="active",
            display_name=body.display_name,
        )
        return user
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Google Mailboxes ──────────────────────────────────────────────

class MailboxCreateRequest(BaseModel):
    company_id: int
    user_id: uuid.UUID
    email_address: str
    token_json: Any


def _mailbox_dict(m) -> dict:
    return {
        "google_mailbox_id": m.google_mailbox_id,
        "company_id": m.company_id,
        "user_id": m.user_id,
        "email_address": m.email_address,
        "token_json": m.token_json,
        "last_history_id": m.last_history_id,
        "watch_expiration": m.watch_expiration,
    }


@router.post("/mailboxes", status_code=201)
async def create_mailbox(body: MailboxCreateRequest):
    try:
        m = await asyncio.to_thread(
            crud_google_mailboxes.create_google_mailbox,
            body.company_id,
            user_id=body.user_id,
            email_address=body.email_address,
            token_json=body.token_json,
        )
        return _mailbox_dict(m)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


class MailboxTokenUpdate(BaseModel):
    token_json: Any


@router.patch("/mailboxes/{google_mailbox_id}/token")
async def update_mailbox_token(google_mailbox_id: int, body: MailboxTokenUpdate):
    m = await asyncio.to_thread(
        crud_google_mailboxes.update_google_mailbox_token,
        google_mailbox_id,
        token_json=body.token_json,
    )
    if not m:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return _mailbox_dict(m)


class MailboxHistoryIdUpdate(BaseModel):
    last_history_id: str | None


@router.patch("/mailboxes/{google_mailbox_id}/history-id")
async def update_mailbox_history_id(google_mailbox_id: int, body: MailboxHistoryIdUpdate):
    try:
        await asyncio.to_thread(
            crud_google_mailboxes.set_google_mailbox_history_id,
            google_mailbox_id,
            last_history_id=body.last_history_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


class MailboxWatchExpirationUpdate(BaseModel):
    watch_expiration: datetime | None


@router.patch("/mailboxes/{google_mailbox_id}/watch-expiration")
async def update_mailbox_watch_expiration(google_mailbox_id: int, body: MailboxWatchExpirationUpdate):
    await asyncio.to_thread(
        crud_google_mailboxes.update_google_mailbox_watch_expiration,
        google_mailbox_id,
        watch_expiration=body.watch_expiration,
    )
    return {"ok": True}


@router.get("/mailboxes/by-email-global")
async def get_mailbox_by_email_global(email: str):
    """Look up a mailbox by email across all companies (no company_id filter)."""
    m = await asyncio.to_thread(crud_google_mailboxes.get_google_mailbox_by_email_global, email)
    if not m:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return _mailbox_dict(m)


# ── Companies ─────────────────────────────────────────────────────

@router.get("/companies")
async def list_companies_internal():
    companies = await asyncio.to_thread(companies_crud.list_companies)
    return [
        {"company_id": c.company_id, "name": c.name}
        for c in companies
    ]


@router.delete("/companies/{company_id}", status_code=204)
async def hard_delete_company_internal(company_id: int):
    """Hard-delete a company and all its children (CASCADE).
    Intended for test teardown only — not exposed to end users."""
    deleted = await asyncio.to_thread(companies_crud.hard_delete_company, company_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company not found")


# ── Slack Workspaces ──────────────────────────────────────────────

class SlackWorkspaceCreateRequest(BaseModel):
    company_id: int
    team_id: str
    access_token: str


@router.post("/slack/workspaces", response_model=SlackWorkspaceRead, status_code=201)
async def create_slack_workspace_internal(body: SlackWorkspaceCreateRequest):
    try:
        ws = await asyncio.to_thread(
            slack_workspaces_crud.create_slack_workspace,
            body.company_id,
            team_id=body.team_id,
            access_token=body.access_token,
        )
        return ws
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


class SlackWorkspaceTokenUpdate(BaseModel):
    access_token: str


@router.patch("/slack/workspaces/{team_id}/token", response_model=SlackWorkspaceRead)
async def update_slack_workspace_token(team_id: str, body: SlackWorkspaceTokenUpdate):
    ws = await asyncio.to_thread(
        slack_workspaces_crud.update_slack_workspace_access_token,
        team_id,
        access_token=body.access_token,
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


# ── Slack Accounts ────────────────────────────────────────────────

class SlackAccountCreateRequest(BaseModel):
    company_id: int
    team_id: str
    slack_user_id: str
    user_id: uuid.UUID
    email: str | None = None


@router.post("/slack/accounts", response_model=SlackAccountRead, status_code=201)
async def create_slack_account_internal(body: SlackAccountCreateRequest):
    try:
        acct = await asyncio.to_thread(
            crud_slack_accounts.create_slack_account,
            body.company_id,
            team_id=body.team_id,
            slack_user_id=body.slack_user_id,
            user_id=body.user_id,
            email=body.email,
        )
        return acct
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


class SlackAccountEmailUpdate(BaseModel):
    email: str | None = None


@router.patch("/slack/accounts/{team_id}/{slack_user_id}/email")
async def update_slack_account_email_internal(team_id: str, slack_user_id: str, body: SlackAccountEmailUpdate):
    await asyncio.to_thread(
        crud_slack_accounts.update_slack_account_email,
        team_id,
        slack_user_id,
        email=body.email,
    )
    return {"ok": True}


# ── Incident Scores ───────────────────────────────────────────────

class IncidentScoresCreate(BaseModel):
    neutral_score: float = 0.0
    humor_sarcasm_score: float = 0.0
    stress_score: float = 0.0
    burnout_score: float = 0.0
    depression_score: float = 0.0
    harassment_score: float = 0.0
    suicidal_ideation_score: float = 0.0
    predicted_category: str | None = None
    predicted_severity: int | None = None


@router.post("/incidents/{message_id}/scores", status_code=201)
async def create_incident_scores_internal(message_id: uuid.UUID, body: IncidentScoresCreate):
    try:
        await asyncio.to_thread(
            crud_incident_scores.create_incident_scores,
            message_id,
            neutral_score=body.neutral_score,
            humor_sarcasm_score=body.humor_sarcasm_score,
            stress_score=body.stress_score,
            burnout_score=body.burnout_score,
            depression_score=body.depression_score,
            harassment_score=body.harassment_score,
            suicidal_ideation_score=body.suicidal_ideation_score,
            predicted_category=body.predicted_category,
            predicted_severity=body.predicted_severity,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}
