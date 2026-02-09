"""
Seed default subscription plans into the database.
Also creates corresponding Stripe Products + Prices if STRIPE_SECRET_KEY is set.
Run once on first startup via the /admin/seed endpoint or on app boot.
"""

import json
import logging

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import SubscriptionPlan

logger = logging.getLogger(__name__)
settings = get_settings()

# SentinelAI pricing tiers (GBP)
DEFAULT_PLANS = [
    {
        "name": "Starter",
        "description": "For small teams getting started with workplace wellbeing.",
        "price_monthly": 49.00,
        "price_yearly": 470.00,   # ~20% annual discount
        "max_employees": 25,
        "features": json.dumps([
            "Basic sentiment analysis",
            "Weekly wellbeing reports",
            "Email alerts",
            "1 Slack workspace integration",
        ]),
    },
    {
        "name": "Professional",
        "description": "For growing companies that need deeper insights.",
        "price_monthly": 149.00,
        "price_yearly": 1430.00,
        "max_employees": 100,
        "features": json.dumps([
            "Advanced AI analysis",
            "Real-time dashboard",
            "Daily wellbeing reports",
            "Slack + Teams integration",
            "Manager alerts & recommendations",
            "Trend analytics",
        ]),
    },
    {
        "name": "Enterprise",
        "description": "For large organisations requiring full-suite capabilities.",
        "price_monthly": 399.00,
        "price_yearly": 3830.00,
        "max_employees": 999999,  # unlimited
        "features": json.dumps([
            "Everything in Professional",
            "Unlimited employees",
            "Custom AI model training",
            "Dedicated account manager",
            "SSO / SAML integration",
            "API access",
            "Priority support",
            "On-premise deployment option",
        ]),
    },
]


async def seed_plans(db: AsyncSession) -> list[SubscriptionPlan]:
    """Insert default plans if they don't already exist. Returns created/existing plans."""
    plans: list[SubscriptionPlan] = []

    for plan_data in DEFAULT_PLANS:
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == plan_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            plans.append(existing)
            continue

        plan = SubscriptionPlan(**plan_data)

        # If Stripe key is configured, create Products + Prices
        if settings.STRIPE_SECRET_KEY:
            try:
                product = stripe.Product.create(
                    name=f"SentinelAI — {plan_data['name']}",
                    description=plan_data["description"],
                    metadata={"plan_name": plan_data["name"]},
                )
                price_monthly = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan_data["price_monthly"] * 100),
                    currency="gbp",
                    recurring={"interval": "month"},
                )
                price_yearly = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan_data["price_yearly"] * 100),
                    currency="gbp",
                    recurring={"interval": "year"},
                )
                plan.stripe_price_id_monthly = price_monthly.id
                plan.stripe_price_id_yearly = price_yearly.id
                logger.info(f"Created Stripe product for plan: {plan_data['name']}")
            except stripe.error.StripeError as e:
                logger.warning(f"Stripe product creation failed for {plan_data['name']}: {e}")

        db.add(plan)
        plans.append(plan)

    await db.commit()
    logger.info(f"Seeded {len(plans)} subscription plans")
    return plans
