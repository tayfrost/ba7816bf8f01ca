import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_current_user, require_role
from database.services import crud_google_mailboxes
from database.services import slack_workspaces_crud

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    provider: str
    connected: bool
    connectedAt: str | None = None


@router.get("", response_model=list[IntegrationStatus])
async def get_integrations(user: CurrentUser = Depends(get_current_user)):
    workspaces = await asyncio.to_thread(
        slack_workspaces_crud.list_slack_workspaces_for_company, user.company_id, include_revoked=False
    )
    mailboxes = await asyncio.to_thread(
        crud_google_mailboxes.list_google_mailboxes_for_company, user.company_id
    )
    return [
        IntegrationStatus(provider="slack", connected=len(workspaces) > 0),
        IntegrationStatus(provider="gmail", connected=len(mailboxes) > 0),
        IntegrationStatus(provider="outlook", connected=False),
    ]


@router.post("/{provider}/start")
async def start_integration(
    provider: str,
    user: CurrentUser = Depends(require_role("biller", "admin")),
):
    login_paths = {
        "slack": f"/slack/oauth/login?company_id={user.company_id}",
        "gmail": f"/gmail/oauth/login?company_id={user.company_id}",
    }
    if provider not in login_paths:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")
    return {"url": login_paths[provider]}


@router.post("/gmail/personal/start")
async def start_personal_gmail(user: CurrentUser = Depends(get_current_user)):
    """
    Any authenticated user (including viewers) can connect their own Gmail mailbox.
    Uses the same OAuth flow but does not require admin/biller role.
    """
    return {"url": f"/gmail/oauth/login?company_id={user.company_id}"}


@router.post("/gmail/member/start")
async def start_member_gmail(user: CurrentUser = Depends(get_current_user)):
    """
    Team member self-registration flow. Any authenticated user can connect their
    Gmail mailbox. The OAuth callback redirects back to /register-gmail instead
    of /connect-accounts so the experience is scoped to this simpler page.
    """
    return {"url": f"/gmail/oauth/login?company_id={user.company_id}&return_page=register-gmail"}


@router.delete("/{provider}", status_code=status.HTTP_200_OK)
async def disconnect_integration(
    provider: str,
    user: CurrentUser = Depends(require_role("biller", "admin")),
):
    if provider == "slack":
        workspaces = await asyncio.to_thread(
            slack_workspaces_crud.list_slack_workspaces_for_company, user.company_id
        )
        for ws in workspaces:
            await asyncio.to_thread(slack_workspaces_crud.revoke_slack_workspace, ws.team_id)
    elif provider == "gmail":
        mailboxes = await asyncio.to_thread(
            crud_google_mailboxes.list_google_mailboxes_for_company, user.company_id
        )
        for mb in mailboxes:
            await asyncio.to_thread(crud_google_mailboxes.hard_delete_google_mailbox, mb.google_mailbox_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")
    return {"detail": f"{provider} disconnected"}
