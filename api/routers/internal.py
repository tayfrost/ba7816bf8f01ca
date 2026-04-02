"""Internal endpoints for service-to-service calls. No JWT required."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from api.models.flagged_incident import FlaggedIncident
from api.models.google_mailbox import GoogleMailbox
from api.models.slack import SlackUser, SlackWorkspace
from api.models.user import SaasUserData
from api.schemas.incident import FlaggedIncidentCreate, FlaggedIncidentRead
from api.schemas.slack import SlackUserRead, SlackWorkspaceRead
from api.schemas.user import UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


# ── Users ──────────────────────────────────────────────────────────

@router.get("/users/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(SaasUserData, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Google Mailboxes ───────────────────────────────────────────────

@router.get("/mailboxes/by-email")
async def get_mailbox_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleMailbox).where(GoogleMailbox.email_address == email)
    )
    mailbox = result.scalar_one_or_none()
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
async def get_mailboxes_for_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleMailbox).where(GoogleMailbox.company_id == company_id)
    )
    mailboxes = result.scalars().all()
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


# ── Slack ──────────────────────────────────────────────────────────

@router.get("/slack/workspace/{team_id}", response_model=SlackWorkspaceRead)
async def get_workspace_by_team_id(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.team_id == team_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/slack/user/{team_id}/{slack_user_id}", response_model=SlackUserRead)
async def get_slack_user(
    team_id: str,
    slack_user_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackUser).where(
            SlackUser.team_id == team_id,
            SlackUser.slack_user_id == slack_user_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Slack user not found")
    return user


# ── Incidents (no auth) ───────────────────────────────────────────

@router.post("/incidents", response_model=FlaggedIncidentRead, status_code=201)
async def create_incident_internal(
    body: FlaggedIncidentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a flagged incident. No JWT needed — for internal service calls."""
    # figure out company_id from workspace
    result = await db.execute(
        select(SlackWorkspace.company_id).where(SlackWorkspace.team_id == body.team_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=400, detail=f"No workspace found for team_id {body.team_id}")
    company_id = row[0]

    if body.email:
        await _try_link_accounts(db, body.team_id, body.slack_user_id, body.email, company_id)

    incident = FlaggedIncident(
        company_id=company_id,
        team_id=body.team_id,
        slack_user_id=body.slack_user_id,
        message_ts=body.message_ts,
        channel_id=body.channel_id,
        raw_message_text=body.raw_message_text,
        class_reason=body.class_reason,
        recommendation=body.recommendation,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


# ── Canonical link-or-create ──────────────────────────────────────

class LinkAccountRequest(BaseModel):
    source: str  # "slack" or "gmail"
    email: str
    # slack fields (optional)
    team_id: str | None = None
    slack_user_id: str | None = None
    slack_name: str | None = None
    slack_surname: str | None = None
    # google fields (optional)
    company_id: int | None = None


@router.post("/link-account")
async def link_or_create_account(
    body: LinkAccountRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical endpoint: accept a source (slack/gmail) + email,
    try to link to an existing account on the other platform,
    or create a new record if it doesn't exist yet.
    """
    if body.source == "slack":
        if not body.team_id or not body.slack_user_id:
            raise HTTPException(status_code=400, detail="team_id and slack_user_id required for slack source")

        # find or create slack user
        result = await db.execute(
            select(SlackUser).where(
                SlackUser.team_id == body.team_id,
                SlackUser.slack_user_id == body.slack_user_id,
            )
        )
        slack_user = result.scalar_one_or_none()

        if not slack_user:
            slack_user = SlackUser(
                team_id=body.team_id,
                slack_user_id=body.slack_user_id,
                name=body.slack_name or "Unknown",
                surname=body.slack_surname or "User",
                status="active",
                email=body.email,
            )
            db.add(slack_user)
            await db.flush()
            logger.info("created new slack user %s in team %s", body.slack_user_id, body.team_id)

        # update email if not set
        if not slack_user.email:
            slack_user.email = body.email

        # try link to google mailbox
        linked_mailbox = None
        if not slack_user.google_mailbox_id:
            mb_result = await db.execute(
                select(GoogleMailbox).where(GoogleMailbox.email_address == body.email)
            )
            mailbox = mb_result.scalar_one_or_none()
            if mailbox:
                slack_user.google_mailbox_id = mailbox.google_mailbox_id
                linked_mailbox = mailbox.email_address
                logger.info("linked slack %s to gmail %s", body.slack_user_id, body.email)

        await db.commit()
        return {
            "source": "slack",
            "slack_user_id": body.slack_user_id,
            "team_id": body.team_id,
            "email": slack_user.email,
            "linked_gmail": linked_mailbox,
            "status": "linked" if linked_mailbox else "created",
        }

    elif body.source == "gmail":
        if not body.company_id:
            raise HTTPException(status_code=400, detail="company_id required for gmail source")

        # find or create google mailbox
        result = await db.execute(
            select(GoogleMailbox).where(GoogleMailbox.email_address == body.email)
        )
        mailbox = result.scalar_one_or_none()

        if not mailbox:
            mailbox = GoogleMailbox(
                company_id=body.company_id,
                email_address=body.email,
            )
            db.add(mailbox)
            await db.flush()
            logger.info("created new google mailbox for %s", body.email)

        # try link to any slack user with same email
        linked_slack = None
        sl_result = await db.execute(
            select(SlackUser).where(
                SlackUser.email == body.email,
                SlackUser.google_mailbox_id.is_(None),
            )
        )
        slack_users = sl_result.scalars().all()
        for su in slack_users:
            su.google_mailbox_id = mailbox.google_mailbox_id
            linked_slack = su.slack_user_id
            logger.info("linked gmail %s to slack %s", body.email, su.slack_user_id)

        await db.commit()
        return {
            "source": "gmail",
            "email": body.email,
            "google_mailbox_id": mailbox.google_mailbox_id,
            "linked_slack_user": linked_slack,
            "status": "linked" if linked_slack else "created",
        }

    else:
        raise HTTPException(status_code=400, detail="source must be 'slack' or 'gmail'")


async def _try_link_accounts(
    db: AsyncSession, team_id: str, slack_user_id: str, email: str, company_id: int
):
    """Best-effort link slack user to google mailbox via email."""
    try:
        result = await db.execute(
            select(SlackUser).where(
                SlackUser.team_id == team_id,
                SlackUser.slack_user_id == slack_user_id,
            )
        )
        slack_user = result.scalar_one_or_none()
        if not slack_user:
            return

        if not slack_user.email:
            slack_user.email = email

        if slack_user.google_mailbox_id:
            return

        result = await db.execute(
            select(GoogleMailbox).where(
                GoogleMailbox.company_id == company_id,
                GoogleMailbox.email_address == email,
            )
        )
        mailbox = result.scalar_one_or_none()
        if mailbox:
            slack_user.google_mailbox_id = mailbox.google_mailbox_id
            logger.info("linked slack user %s to mailbox %s", slack_user_id, mailbox.google_mailbox_id)

        await db.flush()
    except Exception as e:
        logger.warning("account linking failed for %s: %s", slack_user_id, e)
