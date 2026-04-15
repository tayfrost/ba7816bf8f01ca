from database.database import models as model
from sqlalchemy import select, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import os
import uuid

engine = create_engine(os.environ["DATABASE_URL_SYNC"], echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

# ============================ subscriptions =========================

def create_subscription(company_id: int,plan_id: int,*,status: str,current_period_start: datetime,current_period_end: datetime,session: optional[SASession] = None) -> model.Subscription:
    """
    Create a subscription for a company.
    DB enforces one subscription per company (UNIQUE(company_id)).
    Raises:
        ValueError: invalid inputs / missing company/plan
        RuntimeError: constraint violations
    """
    status = (status or "").strip()
    if status not in VALID_SUBSCRIPTION_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_SUBSCRIPTION_STATUS)}")

    if current_period_start is None or current_period_end is None:
        raise ValueError("current_period_start and current_period_end are required.")
    if current_period_end <= current_period_start:
        raise ValueError("current_period_end must be after current_period_start.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, int(company_id))
        if not company or company.deleted_at is not None:
            raise ValueError(f"company_id={company_id} not found or deleted.")

        plan = session.get(model.SubscriptionPlan, int(plan_id))
        if not plan:
            raise ValueError(f"plan_id={plan_id} not found.")

        # quicj friendly error before DB unique constraint triggers
        existing = session.execute(
            select(model.Subscription).where(model.Subscription.company_id == int(company_id))
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Company already has a subscription (subscription_id={existing.subscription_id})."
            )

        sub = model.Subscription(
            company_id=int(company_id),
            plan_id=int(plan_id),
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        session.add(sub)
        session.flush()
        if own_session:
            session.commit()
        session.refresh(sub)
        return sub

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_subscription: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def get_subscription_by_company_id(company_id: int,*,session: optional[SASession] = None) -> optional[model.Subscription]:
    """Because of UNIQUE(company_id), returns at most one subscription."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Subscription).where(model.Subscription.company_id == int(company_id))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_subscription_by_id(subscription_id: int,*,session: optional[SASession] = None) -> optional[model.Subscription]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.Subscription, int(subscription_id))
    finally:
        if own_session:
            session.close()

def list_subscriptions(*, session: optional[SASession] = None) -> list[model.Subscription]:
    """List all subscriptions (admin/debug)."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Subscription).order_by(model.Subscription.created_at.asc())
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

def update_subscription(subscription_id: int,*,plan_id: int | None = None,status: str | None = None,current_period_start: datetime | None = None,current_period_end: datetime | None = None,
    session: optional[SASession] = None,
) -> optional[model.Subscription]:
    """
    Update subscription fields. Returns updated subscription, or None if not found.
    Does NOT allow changing company_id (treating it as immutable).
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        sub = session.get(model.Subscription, int(subscription_id))
        if not sub:
            return None

        if plan_id is not None:
            plan = session.get(model.SubscriptionPlan, int(plan_id))
            if not plan:
                raise ValueError(f"plan_id={plan_id} not found.")
            sub.plan_id = int(plan_id)

        if status is not None:
            status = status.strip()
            if status not in VALID_SUBSCRIPTION_STATUS:
                raise ValueError(f"status must be one of {sorted(VALID_SUBSCRIPTION_STATUS)}")
            sub.status = status

        if current_period_start is not None:
            sub.current_period_start = current_period_start
        if current_period_end is not None:
            sub.current_period_end = current_period_end

        # validate after possibly changing one/both dates
        if sub.current_period_end <= sub.current_period_start:
            raise ValueError("current_period_end must be after current_period_start.")

        session.commit()
        session.refresh(sub)
        return sub

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_subscription: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def cancel_subscription(subscription_id: int,*,session: optional[SASession] = None) -> bool:
    """
    Convenience: set status='canceled'. Returns False if not found.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        sub = session.get(model.Subscription, int(subscription_id))
        if not sub:
            return False
        sub.status = "canceled"
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def delete_subscription(subscription_id: int,*,session: optional[SASession] = None) -> bool:
    """
    Hard delete subscription row. Returns True if deleted, False if not found.
    NOTE: FK RESTRICT only points from subscriptions -> (companies, subscription_plans),
          so deleting a subscription is usually safe and should not be blocked by other tables.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        sub = session.get(model.Subscription, int(subscription_id))
        if not sub:
            return False
        session.delete(sub)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected delete_subscription: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
