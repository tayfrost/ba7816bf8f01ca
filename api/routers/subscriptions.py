from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_current_user, get_db, require_role
from api.models.subscription import Subscription
from api.models.subscription_plan import SubscriptionPlan
from api.schemas.subscription import SubscriptionCreate, SubscriptionPlanRead, SubscriptionRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=list[SubscriptionPlanRead])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubscriptionPlan))
    return list(result.scalars().all())


@router.get("/current", response_model=SubscriptionRead)
async def get_current_subscription(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.company_id == user.company_id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    return subscription


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    body: SubscriptionCreate,
    user: CurrentUser = Depends(require_role("biller")),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlan, body.plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    subscription = Subscription(
        company_id=user.company_id,
        plan_id=body.plan_id,
        status="active",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription
