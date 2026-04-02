from database.new_database import new_oop as model
from sqlalchemy import select, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from database.new_database.utils import utility_functions as ufunc
import uuid


engine = create_engine("postgresql+psycopg://postgres:postgres@pgvector:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

# ====================== Subscription_plan =================

def create_subscription_plan(plan_name: str,price_pennies: int,seat_limit: int,currency: str = "GBP",session: optional[SASession] = None) -> model.SubscriptionPlan:
    """
    Create a subscription plan.

    Raises:
        ValueError: invalid inputs
        RuntimeError: unique/constraint violations
    """
    plan_name = (plan_name or "").strip()
    currency = (currency or "GBP").strip().upper()

    if len(plan_name) < 2:
        raise ValueError("plan_name must be at least 2 characters (after trimming).")
    if price_pennies is None or int(price_pennies) < 0:
        raise ValueError("price_pennies must be >= 0.")
    if seat_limit is None or int(seat_limit) <= 0:
        raise ValueError("seat_limit must be > 0.")
    if len(currency) != 3:
        raise ValueError("currency must be a 3-letter code like 'GBP'.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        existing = session.execute(
            select(model.SubscriptionPlan).where(model.SubscriptionPlan.plan_name == plan_name)
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Subscription plan '{plan_name}' already exists (plan_id={existing.plan_id})."
            )

        plan = model.SubscriptionPlan(
            plan_name=plan_name,
            price_pennies=int(price_pennies),
            currency=currency,
            seat_limit=int(seat_limit),
        )
        session.add(plan)

        session.flush()
        session.commit()

        session.refresh(plan)
        return plan

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_subscription_plan: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def list_subscription_plans(session: optional[SASession] = None) -> list[model.SubscriptionPlan]:
    """Return all plans ordered by price_pennies then seat_limit then plan_name."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = (
            select(model.SubscriptionPlan)
            .order_by(
                model.SubscriptionPlan.price_pennies.asc(),
                model.SubscriptionPlan.seat_limit.asc(),
                model.SubscriptionPlan.plan_name.asc(),
            )
        )
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

def get_subscription_plan_by_name(plan_name: str, session: optional[SASession] = None) -> optional[model.SubscriptionPlan]:
    """Get a plan by name. Returns None if not found."""
    plan_name = (plan_name or "").strip()
    if not plan_name:
        return None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.SubscriptionPlan).where(model.SubscriptionPlan.plan_name == plan_name)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_subscription_plan_by_id(plan_id: int,session: optional[SASession] = None) -> optional[model.SubscriptionPlan]:
    """Get a plan by id. Returns None if not found."""
    if plan_id is None:
        return None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        return session.get(model.SubscriptionPlan, plan_id)
    finally:
        if own_session:
            session.close()

def update_subscription_plan(plan_id: int,*,plan_name: str | None = None,price_pennies: int | None = None,seat_limit: int | None = None,currency: str | None = None,session: optional[SASession] = None) -> optional[model.SubscriptionPlan]:
    """
    Update a plan by id. Returns updated plan, or None if not found.
    Only updates fields you pass, others will be unchanged.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        plan = session.get(model.SubscriptionPlan, plan_id)
        if not plan:
            return None

        if plan_name is not None:
            plan_name = plan_name.strip()
            if len(plan_name) < 2:
                raise ValueError("plan_name must be at least 2 characters (after trimming).")
            plan.plan_name = plan_name

        if price_pennies is not None:
            if int(price_pennies) < 0:
                raise ValueError("price_pennies must be >= 0.")
            plan.price_pennies = int(price_pennies)

        if seat_limit is not None:
            if int(seat_limit) <= 0:
                raise ValueError("seat_limit must be > 0.")
            plan.seat_limit = int(seat_limit)

        if currency is not None:
            currency = currency.strip().upper()
            if len(currency) != 3:
                raise ValueError("currency must be a 3-letter code like 'GBP'.")
            plan.currency = currency

        session.commit()
        session.refresh(plan)
        return plan

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_subscription_plan: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def delete_subscription_plan(plan_id: int, session: optional[SASession] = None) -> bool:
    """
    Delete a plan by id.
    Returns True if deleted, False if not found.

    NOTE: Will fail if any subscriptions rows reference the plan (FK RESTRICT).
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        plan = session.get(model.SubscriptionPlan, plan_id)
        if not plan:
            return False

        session.delete(plan)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(
            f"DB rejected delete_subscription_plan (maybe plan is in use): {e.orig}"
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
