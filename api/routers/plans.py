import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import CurrentUser, require_role
from api.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from database.db_service.utils import subscription_plan_crud

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead])
async def list_plans():
    return await asyncio.to_thread(subscription_plan_crud.list_subscription_plans)


@router.get("/{plan_id}", response_model=PlanRead)
async def get_plan(plan_id: int):
    plan = await asyncio.to_thread(subscription_plan_crud.get_subscription_plan_by_id, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanCreate,
    user: CurrentUser = Depends(require_role("admin", "biller")),
):
    try:
        return await asyncio.to_thread(
            subscription_plan_crud.create_subscription_plan,
            body.plan_name, body.price_pennies, body.seat_limit, body.currency,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{plan_id}", response_model=PlanRead)
async def update_plan(
    plan_id: int,
    body: PlanUpdate,
    user: CurrentUser = Depends(require_role("admin", "biller")),
):
    try:
        plan = await asyncio.to_thread(
            subscription_plan_crud.update_subscription_plan, plan_id,
            plan_name=body.plan_name,
            price_pennies=body.price_pennies,
            seat_limit=body.seat_limit,
            currency=body.currency,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_200_OK)
async def delete_plan(
    plan_id: int,
    user: CurrentUser = Depends(require_role("admin", "biller")),
):
    try:
        deleted = await asyncio.to_thread(subscription_plan_crud.delete_subscription_plan, plan_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return {"detail": "Plan deleted"}
