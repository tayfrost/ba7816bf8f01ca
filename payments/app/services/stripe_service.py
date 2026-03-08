"""
Stripe integration service.
Handles: customer creation, checkout sessions, subscriptions,
         portal sessions, and webhook event processing.

Uses shared tables: companies, subscription_plan (from feature/database)
Owns tables: subscriptions, payments, stripe_events
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import (
    Company,
    Payment,
    PaymentStatus,
    StripeEvent,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)
settings = get_settings()

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:

    # ── Customer management ───────────────────────

    @staticmethod
    async def get_or_create_stripe_customer(
        db: AsyncSession,
        company: Company,
    ) -> str:
        """Return existing Stripe customer ID or create a new one."""
        if company.stripe_customer_id:
            return company.stripe_customer_id

        customer = stripe.Customer.create(
            name=company.company_name,
            metadata={"company_id": str(company.company_id)},
        )
        company.stripe_customer_id = customer.id
        db.add(company)
        await db.commit()
        await db.refresh(company)
        return customer.id

    # ── Checkout ──────────────────────────────────

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        company_id: int,
        plan_id: int,
        interval: str = "month",
    ) -> dict:
        """Create a Stripe Checkout session for a new subscription."""

        # Fetch company
        result = await db.execute(
            select(Company).where(Company.company_id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Fetch plan
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Subscription plan {plan_id} not found")

        # Determine Stripe Price ID
        price_id = (
            plan.stripe_price_id_monthly if interval == "month"
            else plan.stripe_price_id_yearly
        )
        if not price_id:
            raise ValueError(
                f"Plan '{plan.plan_name}' has no Stripe price for interval '{interval}'"
            )

        # Ensure Stripe customer exists
        customer_id = await StripeService.get_or_create_stripe_customer(db, company)

        # Build checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=(
                f"{settings.FRONTEND_URL}/payments/success"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.FRONTEND_URL}/payments/cancel",
            metadata={
                "company_id": str(company_id),
                "plan_id": str(plan_id),
                "interval": interval,
            },
            subscription_data={
                "metadata": {
                    "company_id": str(company_id),
                    "plan_id": str(plan_id),
                },
            },
        )

        return {"checkout_url": session.url, "session_id": session.id}

    # ── Subscription management ───────────────────

    @staticmethod
    async def get_subscription(
        db: AsyncSession,
        company_id: int,
    ) -> Optional[Subscription]:
        """Get the active subscription for a company."""
        result = await db.execute(
            select(Subscription)
            .where(Subscription.company_id == company_id)
            .where(
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIALING.value,
                    SubscriptionStatus.PAST_DUE.value,
                ])
            )
            .order_by(Subscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        company_id: int,
        cancel_at_period_end: bool = True,
    ) -> Subscription:
        """Cancel a subscription (immediately or at period end)."""
        sub = await StripeService.get_subscription(db, company_id)
        if not sub:
            raise ValueError("No active subscription found")

        if cancel_at_period_end:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            sub.cancel_at_period_end = True
        else:
            stripe.Subscription.cancel(sub.stripe_subscription_id)
            sub.status = SubscriptionStatus.CANCELED.value
            sub.canceled_at = datetime.now(timezone.utc)

        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    # ── Customer portal ───────────────────────────

    @staticmethod
    async def create_customer_portal_session(
        db: AsyncSession,
        company_id: int,
    ) -> str:
        """Create a Stripe Customer Portal session (manage billing)."""
        result = await db.execute(
            select(Company).where(Company.company_id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company or not company.stripe_customer_id:
            raise ValueError("Company has no Stripe customer")

        session = stripe.billing_portal.Session.create(
            customer=company.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard",
        )
        return session.url

    # ── Webhook processing ────────────────────────

    @staticmethod
    async def handle_webhook_event(
        db: AsyncSession,
        payload: bytes,
        sig_header: str,
    ) -> dict:
        """Verify and process an incoming Stripe webhook event."""

        # 1. Verify signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid Stripe webhook signature")

        # 2. Idempotency check
        existing = await db.execute(
            select(StripeEvent).where(StripeEvent.stripe_event_id == event["id"])
        )
        if existing.scalar_one_or_none():
            return {"status": "already_processed"}

        # 3. Log the event
        stripe_event = StripeEvent(
            stripe_event_id=event["id"],
            event_type=event["type"],
            payload=json.dumps(event["data"]),
        )
        db.add(stripe_event)

        # 4. Route to handler
        try:
            handler = EVENT_HANDLERS.get(event["type"])
            if handler:
                await handler(db, event["data"]["object"])
            else:
                logger.info(f"Unhandled Stripe event type: {event['type']}")

            stripe_event.processed = True
        except Exception as e:
            logger.error(f"Error processing {event['type']}: {e}")
            stripe_event.error_message = str(e)

        await db.commit()
        return {"status": "processed", "type": event["type"]}


# ──────────────────────────────────────────────
# Individual event handlers
# ──────────────────────────────────────────────

async def _handle_checkout_completed(db: AsyncSession, session_obj: dict) -> None:
    """checkout.session.completed — create local subscription record."""
    metadata = session_obj.get("metadata", {})
    company_id = metadata.get("company_id")
    plan_id = metadata.get("plan_id")
    interval = metadata.get("interval", "month")
    stripe_sub_id = session_obj.get("subscription")

    if not (company_id and plan_id and stripe_sub_id):
        logger.warning("Checkout completed but missing metadata")
        return

    # Fetch Stripe subscription for period info
    stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)

    subscription = Subscription(
        company_id=int(company_id),
        plan_id=int(plan_id),
        stripe_subscription_id=stripe_sub_id,
        status=SubscriptionStatus.ACTIVE.value,
        interval=interval,
        current_period_start=datetime.fromtimestamp(
            stripe_sub.current_period_start, tz=timezone.utc
        ),
        current_period_end=datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        ),
    )
    db.add(subscription)


async def _handle_invoice_paid(db: AsyncSession, invoice: dict) -> None:
    """invoice.paid — record a successful payment."""
    customer_id = invoice.get("customer")

    result = await db.execute(
        select(Company).where(Company.stripe_customer_id == customer_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        logger.warning(f"Invoice paid for unknown customer: {customer_id}")
        return

    payment = Payment(
        company_id=company.company_id,
        stripe_payment_intent_id=invoice.get("payment_intent"),
        stripe_invoice_id=invoice.get("id"),
        amount_pennies=invoice.get("amount_paid", 0),  # Stripe already in pennies
        currency=invoice.get("currency", "gbp").upper(),
        status=PaymentStatus.SUCCEEDED.value,
        description=f"Invoice {invoice.get('number', 'N/A')}",
    )
    db.add(payment)


async def _handle_invoice_payment_failed(db: AsyncSession, invoice: dict) -> None:
    """invoice.payment_failed — mark subscription as past_due."""
    sub_id = invoice.get("subscription")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = SubscriptionStatus.PAST_DUE.value
        db.add(sub)


async def _handle_subscription_updated(db: AsyncSession, stripe_sub: dict) -> None:
    """customer.subscription.updated — sync status from Stripe."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    valid_statuses = {s.value for s in SubscriptionStatus}
    new_status = stripe_sub.get("status")
    if new_status in valid_statuses:
        sub.status = new_status

    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    sub.current_period_start = datetime.fromtimestamp(
        stripe_sub["current_period_start"], tz=timezone.utc
    )
    sub.current_period_end = datetime.fromtimestamp(
        stripe_sub["current_period_end"], tz=timezone.utc
    )
    db.add(sub)


async def _handle_subscription_deleted(db: AsyncSession, stripe_sub: dict) -> None:
    """customer.subscription.deleted — mark local subscription as canceled."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub["id"]
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = SubscriptionStatus.CANCELED.value
        sub.canceled_at = datetime.now(timezone.utc)
        db.add(sub)


# Event type → handler mapping
EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
}
