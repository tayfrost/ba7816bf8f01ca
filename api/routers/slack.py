from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db, require_role
from api.models.slack import SlackAccount, SlackWorkspace
from api.models.user import User
from api.schemas.slack import SlackAccountRead, SlackWorkspaceRead

router = APIRouter(prefix="/integrations/slack", tags=["slack"])


@router.post("/install", response_model=SlackWorkspaceRead, status_code=status.HTTP_201_CREATED)
async def install_workspace(
    team_id: str,
    access_token: str,
    user: User = Depends(require_role("biller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    workspace = SlackWorkspace(
        company_id=user.company_id,
        team_id=team_id,
        access_token=access_token,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/workspaces", response_model=list[SlackWorkspaceRead])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackWorkspace).where(
            SlackWorkspace.company_id == user.company_id,
            SlackWorkspace.revoked_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
async def revoke_workspace(
    workspace_id: int,
    user: User = Depends(require_role("biller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackWorkspace).where(
            SlackWorkspace.slack_workspace_id == workspace_id,
            SlackWorkspace.company_id == user.company_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    workspace.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"detail": "Workspace revoked"}


@router.get("/accounts", response_model=list[SlackAccountRead])
async def list_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackAccount).where(SlackAccount.company_id == user.company_id)
    )
    return list(result.scalars().all())
