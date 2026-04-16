import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from database.services import companies_crud
from database.services import subscriptions_crud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(body: CompanyCreate):
    company = None
    try:
        company = await asyncio.to_thread(companies_crud.create_company, body.name)
        now = datetime.now(timezone.utc)
        await asyncio.to_thread(
            subscriptions_crud.create_subscription,
            company.company_id, body.plan_id,
            status="trialing",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        return company
    except (ValueError, RuntimeError) as e:
        if company is not None:
            # Subscription creation failed — roll back the company to avoid orphaned rows.
            try:
                await asyncio.to_thread(companies_crud.hard_delete_company, company.company_id)
            except Exception:
                logger.error(
                    f"Failed to roll back company_id={company.company_id} after subscription error: {e}"
                )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=CompanyRead)
async def get_my_company(user: CurrentUser = Depends(get_current_user)):
    company = await asyncio.to_thread(companies_crud.get_company_by_id, user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyRead)
async def update_my_company(
    body: CompanyUpdate,
    user: CurrentUser = Depends(require_role("biller", "admin")),
):
    try:
        company = await asyncio.to_thread(
            companies_crud.update_company, user.company_id, name=body.name
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_my_company(user: CurrentUser = Depends(require_role("biller"))):
    deleted = await asyncio.to_thread(companies_crud.hard_delete_company_cascade, user.company_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return {"detail": "Company deleted"}
