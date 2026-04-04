import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.slack import SlackAccountRead, SlackWorkspaceRead
from database.db_service.utils import crud_slack_accounts
from database.db_service.utils import slack_workspaces_crud

router = APIRouter(prefix="/integrations/slack", tags=["slack"])


@router.post("/install", response_model=SlackWorkspaceRead, status_code=status.HTTP_201_CREATED)
async def install_workspace(
    team_id: str,
    access_token: str,
    user: CurrentUser = Depends(require_role("biller", "admin")),
):
    try:
        return await asyncio.to_thread(
            slack_workspaces_crud.create_slack_workspace,
            user.company_id, team_id=team_id, access_token=access_token,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/workspaces", response_model=list[SlackWorkspaceRead])
async def list_workspaces(user: CurrentUser = Depends(get_current_user)):
    return await asyncio.to_thread(
        slack_workspaces_crud.list_slack_workspaces_for_company, user.company_id
    )


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_workspace(
    workspace_id: int,
    user: CurrentUser = Depends(require_role("biller", "admin")),
):
    ws = await asyncio.to_thread(slack_workspaces_crud.get_slack_workspace_by_id, workspace_id)
    if not ws or ws.company_id != user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    revoked = await asyncio.to_thread(slack_workspaces_crud.revoke_slack_workspace, ws.team_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace already revoked")
    return {"detail": "Workspace revoked"}


@router.get("/users", response_model=list[SlackAccountRead])
async def list_slack_users(user: CurrentUser = Depends(get_current_user)):
    return await asyncio.to_thread(
        crud_slack_accounts.list_slack_accounts_for_company, user.company_id
    )
