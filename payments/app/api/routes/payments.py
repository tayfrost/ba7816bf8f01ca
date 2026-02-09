"""
Payment API routes.
Endpoints: plans, organizations, checkout, subscriptions, payments, portal.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Organization, Payment, Subscription, SubscriptionPlan
from app.schemas.schemas import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    MessageResponse,
    OrganizationCreate,
    OrganizationResponse,
    PaymentResponse,
    SubscriptionCancel,
    SubscriptionPlanResponse,
    SubscriptionResponse,
)
from app.services.stripe_service import StripeService

router = APIRouter()


# ──────────────────────────────────────────────
# Subscription Plans
# ──────────────────────────────────────────────

@router.get(
    "/plans",
    response_model=list[SubscriptionPlanResponse],
    summary="List all available subscription plans",
)
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
    )
    return result.scalars().all()


@router.get(
    "/plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    summary="Get a single subscription plan by ID",
)
async def get_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# ──────────────────────────────────────────────
# Organizations
# ──────────────────────────────────────────────

@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization",
)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate email
    existing = await db.execute(
        select(Organization).where(Organization.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Organization with this email already exists",
        )

    org = Organization(**data.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get(
    "/organizations/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization details",
)
async def get_organization(org_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ──────────────────────────────────────────────
# Checkout
# ──────────────────────────────────────────────

@router.post(
    "/checkout",
    response_model=CheckoutSessionResponse,
    summary="Create a Stripe Checkout session for a new subscription",
)
async def create_checkout_session(
    data: CheckoutSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await StripeService.create_checkout_session(
            db=db,
            organization_id=data.organization_id,
            plan_id=data.plan_id,
            interval=data.interval,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# Subscriptions
# ──────────────────────────────────────────────

@router.get(
    "/subscriptions/{org_id}",
    response_model=Optional[SubscriptionResponse],
    summary="Get active subscription for an organization",
)
async def get_subscription(org_id: UUID, db: AsyncSession = Depends(get_db)):
    sub = await StripeService.get_subscription(db, org_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub


@router.post(
    "/subscriptions/{org_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel a subscription",
)
async def cancel_subscription(
    org_id: UUID,
    data: SubscriptionCancel,
    db: AsyncSession = Depends(get_db),
):
    try:
        sub = await StripeService.cancel_subscription(
            db=db,
            organization_id=org_id,
            cancel_at_period_end=data.cancel_at_period_end,
        )
        return sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# Payment History
# ──────────────────────────────────────────────

@router.get(
    "/payments/{org_id}",
    response_model=list[PaymentResponse],
    summary="List payment history for an organization",
)
async def list_payments(
    org_id: UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment)
        .where(Payment.organization_id == org_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ──────────────────────────────────────────────
# Customer Portal
# ──────────────────────────────────────────────

@router.post(
    "/portal/{org_id}",
    response_model=CustomerPortalResponse,
    summary="Create a Stripe Customer Portal session",
)
async def create_portal_session(org_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        url = await StripeService.create_customer_portal_session(db, org_id)
        return {"portal_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
