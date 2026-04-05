import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.user import UserRoleRead, UserUpdate
from api.services.auth_service import hash_password
from database.services import crud_auth_users
from database.services import users_crud

router = APIRouter(prefix="/users", tags=["users"])


def _to_role_read(user, email: str = "") -> UserRoleRead:
    return UserRoleRead(
        user_id=user.user_id,
        company_id=user.company_id,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email=email,
    )


@router.get("", response_model=list[UserRoleRead])
async def list_users(user: CurrentUser = Depends(get_current_user)):
    users = await asyncio.to_thread(users_crud.list_users, user.company_id)
    result = []
    for u in users:
        auth = await asyncio.to_thread(crud_auth_users.get_auth_user_by_user_id, user.company_id, u.user_id)
        result.append(_to_role_read(u, auth.email if auth else ""))
    return result


@router.get("/{user_id}", response_model=UserRoleRead)
async def get_user(user_id: uuid.UUID, user: CurrentUser = Depends(get_current_user)):
    target = await asyncio.to_thread(users_crud.get_user_by_id, user.company_id, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    auth = await asyncio.to_thread(crud_auth_users.get_auth_user_by_user_id, user.company_id, user_id)
    return _to_role_read(target, auth.email if auth else "")


@router.post("/invite", response_model=UserRoleRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    company_id: int,
    email: str,
    display_name: str | None = None,
    role: str = "viewer",
):
    try:
        new_user = await asyncio.to_thread(
            users_crud.create_user, company_id,
            role=role, status="active", display_name=display_name,
        )
        await asyncio.to_thread(
            crud_auth_users.create_auth_user, company_id,
            email=email.lower().strip(),
            password_hash=hash_password("changeme"),
            user_id=new_user.user_id,
        )
        return _to_role_read(new_user, email)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{user_id}", response_model=UserRoleRead)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    user: CurrentUser = Depends(require_role("admin", "biller")),
):
    try:
        updated = await asyncio.to_thread(
            users_crud.update_user, user.company_id, user_id,
            display_name=body.display_name,
            role=body.role,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    auth = await asyncio.to_thread(crud_auth_users.get_auth_user_by_user_id, user.company_id, user_id)
    return _to_role_read(updated, auth.email if auth else "")


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("admin", "biller")),
):
    deleted = await asyncio.to_thread(users_crud.soft_delete_user, user.company_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "User deactivated"}
