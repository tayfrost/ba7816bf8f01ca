from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, require_role
from api.models.subscription_plan import SubscriptionPlan
from api.models.user import User
from api.schemas.plan import PlanCreate, PlanRead, PlanUpdate

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubscriptionPlan))
    return list(result.scalars().all())


@router.get("/{plan_id}", response_model=PlanRead)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanCreate,
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    plan = SubscriptionPlan(
        plan_name=body.plan_name,
        plan_cost_pennies=body.plan_cost_pennies,
        currency=body.currency,
        max_employees=body.max_employees,
        stripe_price_id_monthly=body.stripe_price_id_monthly,
        stripe_price_id_yearly=body.stripe_price_id_yearly,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch("/{plan_id}", response_model=PlanRead)
async def update_plan(
    plan_id: int,
    body: PlanUpdate,
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_200_OK)
async def delete_plan(
    plan_id: int,
    user: User = Depends(require_role("admin", "biller")),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    await db.delete(plan)
    await db.commit()
    return {"detail": "Plan deleted"}
