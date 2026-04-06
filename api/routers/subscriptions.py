import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, get_current_user, require_role
from api.schemas.subscription import SubscriptionCreate, SubscriptionPlanRead, SubscriptionRead
from database.services import subscription_plan_crud
from database.services import subscriptions_crud

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=list[SubscriptionPlanRead])
async def list_plans():
    return await asyncio.to_thread(subscription_plan_crud.list_subscription_plans)


@router.get("/current", response_model=SubscriptionRead)
async def get_current_subscription(user: CurrentUser = Depends(get_current_user)):
    sub = await asyncio.to_thread(subscriptions_crud.get_subscription_by_company_id, user.company_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")
    return sub


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    body: SubscriptionCreate,
    user: CurrentUser = Depends(require_role("biller")),
):
    plan = await asyncio.to_thread(subscription_plan_crud.get_subscription_plan_by_id, body.plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    try:
        return await asyncio.to_thread(
            subscriptions_crud.create_subscription,
            user.company_id, body.plan_id,
            status=body.status,
            current_period_start=body.current_period_start,
            current_period_end=body.current_period_end,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
