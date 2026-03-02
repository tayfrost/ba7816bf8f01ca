"""
Payment API routes.
Uses shared tables: companies, subscription_plan
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Company, Payment, Subscription, SubscriptionPlan
from app.schemas.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    MessageResponse,
    PaymentResponse,
    SubscriptionCancel,
    SubscriptionPlanResponse,
    SubscriptionResponse,
)
from app.services.stripe_service import StripeService

router = APIRouter()


# ── Subscription Plans ────────────────────────

@router.get("/plans", response_model=list[SubscriptionPlanResponse], summary="List subscription plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubscriptionPlan))
    return result.scalars().all()


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse, summary="Get a plan by ID")
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# ── Checkout ──────────────────────────────────

@router.post("/checkout", response_model=CheckoutSessionResponse, summary="Create Stripe Checkout session")
async def create_checkout_session(
    data: CheckoutSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await StripeService.create_checkout_session(
            db=db,
            company_id=data.company_id,
            plan_id=data.plan_id,
            interval=data.interval,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Subscriptions ─────────────────────────────

@router.get(
    "/subscriptions/{company_id}",
    response_model=Optional[SubscriptionResponse],
    summary="Get active subscription for a company",
)
async def get_subscription(company_id: int, db: AsyncSession = Depends(get_db)):
    sub = await StripeService.get_subscription(db, company_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub


@router.post(
    "/subscriptions/{company_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel a subscription",
)
async def cancel_subscription(
    company_id: int,
    data: SubscriptionCancel,
    db: AsyncSession = Depends(get_db),
):
    try:
        sub = await StripeService.cancel_subscription(
            db=db,
            company_id=company_id,
            cancel_at_period_end=data.cancel_at_period_end,
        )
        return sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Payment History ───────────────────────────

@router.get(
    "/payments/{company_id}",
    response_model=list[PaymentResponse],
    summary="List payment history",
)
async def list_payments(
    company_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment)
        .where(Payment.company_id == company_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ── Customer Portal ───────────────────────────

@router.post(
    "/portal/{company_id}",
    response_model=CustomerPortalResponse,
    summary="Create Stripe Customer Portal session",
)
async def create_portal_session(company_id: int, db: AsyncSession = Depends(get_db)):
    try:
        url = await StripeService.create_customer_portal_session(db, company_id)
        return {"portal_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
