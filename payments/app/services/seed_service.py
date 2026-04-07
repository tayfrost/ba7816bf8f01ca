"""
Seed default subscription plans into Derja's subscription_plan table.
Creates corresponding Stripe Products + Prices if STRIPE_SECRET_KEY is set.
"""

import logging

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import SubscriptionPlan

logger = logging.getLogger(__name__)
settings = get_settings()

# SentinelAI pricing tiers — cost in pennies (matches Derja's schema)
DEFAULT_PLANS = [
    {
        "plan_name": "Starter",
        "price_pennies": 4900,       # £49/month
        "currency": "GBP",
        "seat_limit": 25,
    },
    {
        "plan_name": "Professional",
        "price_pennies": 14900,      # £149/month
        "currency": "GBP",
        "seat_limit": 100,
    },
    {
        "plan_name": "Enterprise",
        "price_pennies": 39900,      # £399/month
        "currency": "GBP",
        "seat_limit": 999999,
    },
]


async def seed_plans(db: AsyncSession) -> list[SubscriptionPlan]:
    """Insert default plans if they don't exist. Create Stripe products if key is set."""
    plans: list[SubscriptionPlan] = []

    for plan_data in DEFAULT_PLANS:
        result = await db.execute(
            select(SubscriptionPlan).where(
                SubscriptionPlan.plan_name == plan_data["plan_name"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            plans.append(existing)
            continue

        plan = SubscriptionPlan(**plan_data)

        # Create Stripe Products + Prices if key is configured
        if settings.STRIPE_SECRET_KEY:
            try:
                product = stripe.Product.create(
                    name=f"SentinelAI — {plan_data['plan_name']}",
                    metadata={"plan_name": plan_data["plan_name"]},
                )
                price_monthly = stripe.Price.create(
                    product=product.id,
                    unit_amount=plan_data["price_pennies"],
                    currency="gbp",
                    recurring={"interval": "month"},
                )
                price_yearly = stripe.Price.create(
                    product=product.id,
                    unit_amount=plan_data["price_pennies"] * 10,  # ~20% annual discount
                    currency="gbp",
                    recurring={"interval": "year"},
                )
                plan.stripe_price_id_monthly = price_monthly.id
                plan.stripe_price_id_yearly = price_yearly.id
                logger.info(f"Created Stripe product: {plan_data['plan_name']}")
            except stripe.StripeError as e:
                logger.warning(f"Stripe error for {plan_data['plan_name']}: {e}")

        db.add(plan)
        plans.append(plan)

    await db.commit()
    logger.info(f"Seeded {len(plans)} subscription plans")
    return plans
