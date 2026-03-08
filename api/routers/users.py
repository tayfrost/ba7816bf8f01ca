from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db, require_role
from api.schemas.user import UserRoleRead, UserUpdate
from api.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRoleRead])
async def list_users(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_users_by_company(db, user.company_id)


@router.get("/{user_id}", response_model=UserRoleRead)
async def get_user(
    user_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await user_service.get_user(db, user_id, user.company_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target


@router.post("/invite", response_model=UserRoleRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    email: str,
    name: str,
    surname: str,
    role: str = "viewer",
    user: CurrentUser = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    new_user = await user_service.invite_user(db, user.company_id, email, name, surname, role)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite user. Seat limit may be reached.",
        )
    return new_user


@router.patch("/{user_id}", response_model=UserRoleRead)
async def update_user(
    user_id: int,
    body: UserUpdate,
    new_role: str | None = None,
    user: CurrentUser = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    if new_role:
        updated = await user_service.update_user_role(db, user_id, user.company_id, user.role, new_role)
    else:
        # Update name/surname on saas_user_data
        from api.models.user import SaasUserData
        target_user = await db.get(SaasUserData, user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(target_user, key, value)
        await db.commit()
        updated = await user_service.get_user(db, user_id, user.company_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update denied")
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: int,
    user: CurrentUser = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    deactivated = await user_service.deactivate_user(db, user_id, user.company_id)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "User deactivated"}
