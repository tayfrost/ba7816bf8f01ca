"""Internal endpoints for service-to-service calls. No JWT required."""
import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas.incident import MessageIncidentCreate, MessageIncidentRead
from api.schemas.slack import SlackAccountRead, SlackWorkspaceRead
from api.schemas.user import UserRead
from database.services import crud_auth_users, crud_google_mailboxes, crud_message_incidents, crud_slack_accounts, slack_workspaces_crud
from database.services import users_crud

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
