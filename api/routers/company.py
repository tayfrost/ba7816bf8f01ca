from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db, require_role
from api.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from api.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(body: CompanyCreate, db: AsyncSession = Depends(get_db)):
    company = await company_service.create_company(db, body.company_name, body.plan_id)
    await db.commit()
    return company


@router.get("/me", response_model=CompanyRead)
async def get_my_company(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await company_service.get_company(db, user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyRead)
async def update_my_company(
    body: CompanyUpdate,
    user: CurrentUser = Depends(require_role("biller", "admin")),
    db: AsyncSession = Depends(get_db),
):
    company = await company_service.update_company(db, user.company_id, body.model_dump(exclude_unset=True))
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await db.commit()
    return company


@router.delete("/me", status_code=status.HTTP_200_OK)
async def soft_delete_my_company(
    user: CurrentUser = Depends(require_role("biller")),
    db: AsyncSession = Depends(get_db),
):
    company = await company_service.soft_delete_company(db, user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await db.commit()
    return {"detail": "Company deleted"}
