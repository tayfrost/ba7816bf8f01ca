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
    StripeSubscription,
    SubscriptionPlan,
    StripeSubscriptionStatus,
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
            name=company.name,
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
                f"{settings.FRONTEND_URL}/connect-accounts"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.FRONTEND_URL}/plan",
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
    ) -> Optional[StripeSubscription]:
        """Get the active subscription for a company."""
        result = await db.execute(
            select(StripeSubscription)
            .where(StripeSubscription.company_id == company_id)
            .where(
                StripeSubscription.status.in_([
                    StripeSubscriptionStatus.ACTIVE.value,
                    StripeSubscriptionStatus.TRIALING.value,
                    StripeSubscriptionStatus.PAST_DUE.value,
                ])
            )
            .order_by(StripeSubscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        company_id: int,
        cancel_at_period_end: bool = True,
    ) -> StripeSubscription:
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
            sub.status = StripeSubscriptionStatus.CANCELED.value
            sub.canceled_at = datetime.now(timezone.utc)

        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    # ── Invoices ──────────────────────────────────

    @staticmethod
    def _format_invoice(inv: dict) -> dict:
        """Convert a Stripe invoice object to our InvoiceResponse shape."""
        lines = [
            {
                "description": li.get("description") or "Subscription charge",
                "amount_pennies": li.get("amount", 0),
                "currency": li.get("currency", "gbp").upper(),
            }
            for li in inv.get("lines", {}).get("data", [])
        ]
        return {
            "stripe_invoice_id": inv["id"],
            "number": inv.get("number"),
            "status": inv.get("status", "unknown"),
            "amount_due_pennies": inv.get("amount_due", 0),
            "amount_paid_pennies": inv.get("amount_paid", 0),
            "currency": inv.get("currency", "gbp").upper(),
            "period_start": (
                datetime.fromtimestamp(inv["period_start"], tz=timezone.utc)
                if inv.get("period_start") else None
            ),
            "period_end": (
                datetime.fromtimestamp(inv["period_end"], tz=timezone.utc)
                if inv.get("period_end") else None
            ),
            "invoice_pdf": inv.get("invoice_pdf"),
            "hosted_invoice_url": inv.get("hosted_invoice_url"),
            "lines": lines,
        }

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        company_id: int,
        limit: int = 20,
    ) -> list[dict]:
        """Return the last N Stripe invoices for a company.

        Free-plan companies have no Stripe customer and therefore no invoices —
        we detect this via a join to stripe_subscriptions + subscription_plans and
        return [] silently rather than raising an error.
        """
        result = await db.execute(
            select(Company, SubscriptionPlan)
            .outerjoin(
                StripeSubscription,
                (StripeSubscription.company_id == Company.company_id)
                & (StripeSubscription.status == "active"),
            )
            .outerjoin(
                SubscriptionPlan,
                SubscriptionPlan.plan_id == StripeSubscription.plan_id,
            )
            .where(Company.company_id == company_id)
            .limit(1)
        )
        row = result.first()
        if not row:
            raise ValueError("Company not found")

        company, plan = row

        if not company.stripe_customer_id:
            # Free plan (price_pennies == 0) or no active subscription yet —
            # no Stripe customer is expected, so invoices are simply empty.
            return []

        invoices = stripe.Invoice.list(
            customer=company.stripe_customer_id,
            limit=limit,
        )
        return [StripeService._format_invoice(inv) for inv in invoices.auto_paging_iter()]

    @staticmethod
    async def get_upcoming_invoice(
        db: AsyncSession,
        company_id: int,
    ) -> dict:
        """Return the next upcoming invoice (what the company will be charged next cycle)."""
        result = await db.execute(
            select(Company).where(Company.company_id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company or not company.stripe_customer_id:
            raise ValueError("Company has no Stripe customer")

        try:
            inv = stripe.Invoice.upcoming(customer=company.stripe_customer_id)
        except stripe.error.InvalidRequestError as e:
            raise ValueError(f"No upcoming invoice: {e.user_message}")

        lines = [
            {
                "description": li.get("description") or "Subscription charge",
                "amount_pennies": li.get("amount", 0),
                "currency": li.get("currency", "gbp").upper(),
            }
            for li in inv.get("lines", {}).get("data", [])
        ]
        return {
            "amount_due_pennies": inv.get("amount_due", 0),
            "currency": inv.get("currency", "gbp").upper(),
            "period_start": (
                datetime.fromtimestamp(inv["period_start"], tz=timezone.utc)
                if inv.get("period_start") else None
            ),
            "period_end": (
                datetime.fromtimestamp(inv["period_end"], tz=timezone.utc)
                if inv.get("period_end") else None
            ),
            "lines": lines,
        }

    @staticmethod
    async def send_invoice(
        db: AsyncSession,
        company_id: int,
        stripe_invoice_id: str,
    ) -> dict:
        """
        Send (or resend) a Stripe invoice by email to the customer.
        Only works on invoices in 'open' status.
        """
        result = await db.execute(
            select(Company).where(Company.company_id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company or not company.stripe_customer_id:
            raise ValueError("Company has no Stripe customer")

        # Verify invoice belongs to this customer
        try:
            inv = stripe.Invoice.retrieve(stripe_invoice_id)
        except stripe.error.InvalidRequestError:
            raise ValueError(f"Invoice {stripe_invoice_id} not found")

        if inv.get("customer") != company.stripe_customer_id:
            raise ValueError("Invoice does not belong to this company")

        if inv.get("status") != "open":
            raise ValueError(
                f"Can only send invoices with status 'open' (current: {inv.get('status')})"
            )

        try:
            sent = stripe.Invoice.send_invoice(stripe_invoice_id)
        except stripe.error.StripeError as e:
            raise ValueError(f"Failed to send invoice: {e.user_message}")

        return StripeService._format_invoice(sent)

    # ── Refunds ───────────────────────────────────

    @staticmethod
    async def create_refund(
        db: AsyncSession,
        payment_id: int,
        amount_pennies: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """Refund a payment fully or partially via Stripe."""

        # Fetch payment record
        result = await db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatus.REFUNDED.value:
            raise ValueError("Payment has already been refunded")

        if payment.status != PaymentStatus.SUCCEEDED.value:
            raise ValueError(f"Cannot refund a payment with status '{payment.status}'")

        if not payment.stripe_payment_intent_id:
            raise ValueError("Payment has no Stripe Payment Intent ID — cannot refund")

        # Build Stripe refund params
        refund_params: dict = {"payment_intent": payment.stripe_payment_intent_id}
        if amount_pennies:
            if amount_pennies > payment.amount_pennies:
                raise ValueError(
                    f"Refund amount ({amount_pennies}p) exceeds original "
                    f"payment ({payment.amount_pennies}p)"
                )
            refund_params["amount"] = amount_pennies
        if reason:
            refund_params["reason"] = reason

        # Call Stripe
        try:
            refund = stripe.Refund.create(**refund_params)
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe refund failed: {e.user_message}")

        # Update local payment record
        # Full refund → mark as REFUNDED; partial → keep SUCCEEDED
        refunded_amount = refund.amount
        is_full_refund = (amount_pennies is None) or (amount_pennies >= payment.amount_pennies)
        if is_full_refund:
            payment.status = PaymentStatus.REFUNDED.value

        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return {
            "payment_id": payment.id,
            "stripe_refund_id": refund.id,
            "amount_pennies": refunded_amount,
            "currency": refund.currency.upper(),
            "status": refund.status,
            "reason": reason,
        }

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

    subscription = StripeSubscription(
        company_id=int(company_id),
        plan_id=int(plan_id),
        stripe_subscription_id=stripe_sub_id,
        status=StripeSubscriptionStatus.ACTIVE.value,
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
        select(StripeSubscription).where(StripeSubscription.stripe_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = StripeSubscriptionStatus.PAST_DUE.value
        db.add(sub)


async def _handle_subscription_updated(db: AsyncSession, stripe_sub: dict) -> None:
    """customer.subscription.updated — sync status from Stripe."""
    result = await db.execute(
        select(StripeSubscription).where(
            StripeSubscription.stripe_subscription_id == stripe_sub["id"]
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    valid_statuses = {s.value for s in StripeSubscriptionStatus}
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
        select(StripeSubscription).where(
            StripeSubscription.stripe_subscription_id == stripe_sub["id"]
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = StripeSubscriptionStatus.CANCELED.value
        sub.canceled_at = datetime.now(timezone.utc)
        db.add(sub)


async def _handle_invoice_created(db: AsyncSession, invoice: dict) -> None:
    """
    invoice.created — Stripe just generated a new invoice for the upcoming cycle.
    We log it; Stripe will auto-finalize and charge it (or we can send it manually).
    """
    sub_id = invoice.get("subscription")
    customer_id = invoice.get("customer")
    logger.info(
        f"New invoice created | customer={customer_id} sub={sub_id} "
        f"amount={invoice.get('amount_due')} status={invoice.get('status')}"
    )
    # Nothing to write to DB yet — invoice.paid will record the payment once collected.


async def _handle_invoice_upcoming(db: AsyncSession, invoice: dict) -> None:
    """
    invoice.upcoming — fires ~1 hour before a subscription renews.
    Good hook for sending reminder emails or checking payment method validity.
    """
    sub_id = invoice.get("subscription")
    customer_id = invoice.get("customer")
    amount_due = invoice.get("amount_due", 0)
    logger.info(
        f"Upcoming invoice reminder | customer={customer_id} sub={sub_id} "
        f"amount_due={amount_due}"
    )
    # Extend here: send reminder email, check for expiring cards, etc.


async def _handle_charge_refunded(db: AsyncSession, charge: dict) -> None:
    """charge.refunded — sync refund status back to local payment record."""
    payment_intent_id = charge.get("payment_intent")
    if not payment_intent_id:
        return

    result = await db.execute(
        select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        logger.warning(f"charge.refunded for unknown payment_intent: {payment_intent_id}")
        return

    # amount_refunded is the *total* refunded so far (in pennies)
    amount_refunded = charge.get("amount_refunded", 0)
    amount_captured = charge.get("amount_captured", payment.amount_pennies)

    if amount_refunded >= amount_captured:
        payment.status = PaymentStatus.REFUNDED.value
    # Partial refund — keep SUCCEEDED, Stripe has the source of truth for partial amounts

    db.add(payment)


# Event type → handler mapping
EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "invoice.created": _handle_invoice_created,
    "invoice.upcoming": _handle_invoice_upcoming,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "charge.refunded": _handle_charge_refunded,
}
