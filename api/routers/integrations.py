from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db, require_role
from api.models.google_mailbox import GoogleMailbox
from api.models.slack import SlackWorkspace
from api.models.user import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    provider: str
    connected: bool
    connectedAt: str | None = None


@router.get("", response_model=list[IntegrationStatus])
async def get_integrations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    statuses = []

    # Check Slack
    slack_result = await db.execute(
        select(SlackWorkspace).where(
            SlackWorkspace.company_id == user.company_id,
            SlackWorkspace.revoked_at.is_(None),
        ).limit(1)
    )
    slack_ws = slack_result.scalar_one_or_none()
    statuses.append(IntegrationStatus(
        provider="slack",
        connected=slack_ws is not None,
        connectedAt=slack_ws.installed_at.isoformat() if slack_ws else None,
    ))

    # Check Gmail
    gmail_result = await db.execute(
        select(GoogleMailbox).where(
            GoogleMailbox.company_id == user.company_id,
        ).limit(1)
    )
    gmail_mb = gmail_result.scalar_one_or_none()
    statuses.append(IntegrationStatus(
        provider="gmail",
        connected=gmail_mb is not None,
        connectedAt=None,
    ))

    # Outlook placeholder
    statuses.append(IntegrationStatus(
        provider="outlook",
        connected=False,
        connectedAt=None,
    ))

    return statuses


@router.post("/{provider}/start")
async def start_integration(
    provider: str,
    user: User = Depends(require_role("biller", "admin")),
):
    # OAuth flow stubs — return redirect URLs for each provider
    oauth_urls = {
        "slack": "https://slack.com/oauth/v2/authorize",
        "gmail": "https://accounts.google.com/o/oauth2/v2/auth",
        "outlook": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    }
    if provider not in oauth_urls:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")
    return {"url": oauth_urls[provider]}


@router.delete("/{provider}", status_code=status.HTTP_200_OK)
async def disconnect_integration(
    provider: str,
    user: User = Depends(require_role("biller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if provider == "slack":
        result = await db.execute(
            select(SlackWorkspace).where(
                SlackWorkspace.company_id == user.company_id,
                SlackWorkspace.revoked_at.is_(None),
            )
        )
        workspaces = result.scalars().all()
        for ws in workspaces:
            ws.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    elif provider == "gmail":
        result = await db.execute(
            select(GoogleMailbox).where(GoogleMailbox.company_id == user.company_id)
        )
        mailboxes = result.scalars().all()
        for mb in mailboxes:
            await db.delete(mb)
        await db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")

    return {"detail": f"{provider} disconnected"}
