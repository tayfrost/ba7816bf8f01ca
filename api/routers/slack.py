from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db, require_role
from api.models.slack import SlackUser, SlackWorkspace
from api.schemas.slack import SlackUserRead, SlackWorkspaceRead

router = APIRouter(prefix="/integrations/slack", tags=["slack"])


@router.post("/install", response_model=SlackWorkspaceRead, status_code=status.HTTP_201_CREATED)
async def install_workspace(
    team_id: str,
    access_token: str,
    user: CurrentUser = Depends(require_role("biller", "admin")),
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
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.company_id == user.company_id)
    )
    return list(result.scalars().all())


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_workspace(
    workspace_id: int,
    user: CurrentUser = Depends(require_role("biller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SlackWorkspace).where(
            SlackWorkspace.id == workspace_id,
            SlackWorkspace.company_id == user.company_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    await db.delete(workspace)
    await db.commit()
    return {"detail": "Workspace removed"}


@router.get("/users", response_model=list[SlackUserRead])
async def list_slack_users(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get workspaces for this company, then their users
    ws_result = await db.execute(
        select(SlackWorkspace.team_id).where(SlackWorkspace.company_id == user.company_id)
    )
    team_ids = [row[0] for row in ws_result.all()]
    if not team_ids:
        return []
    result = await db.execute(
        select(SlackUser).where(SlackUser.team_id.in_(team_ids))
    )
    return list(result.scalars().all())
