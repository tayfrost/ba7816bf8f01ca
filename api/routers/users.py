import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db, require_role
from api.models.user import User
from api.schemas.user import UserRead, UserUpdate
from api.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_users_by_company(db, user.company_id)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = await user_service.get_user(db, user_id, user.company_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target


@router.post("/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    email: str,
    display_name: str,
    role: str = "viewer",
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    new_user = await user_service.invite_user(db, user.company_id, email, display_name, role)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite user. Seat limit may be reached.",
        )
    return new_user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    if body.role:
        updated = await user_service.update_user_role(db, user_id, user.company_id, body.role)
    else:
        target = await user_service.get_user(db, user_id, user.company_id)
        if target:
            for key, value in body.model_dump(exclude_unset=True).items():
                setattr(target, key, value)
            await db.commit()
            updated = target
        else:
            updated = None
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update denied")
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: uuid.UUID,
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    deactivated = await user_service.deactivate_user(db, user_id, user.company_id)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "User deactivated"}
