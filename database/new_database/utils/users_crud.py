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

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}
# =============================  USERS TABLE ======================
   
def create_user(company_id: int, *, role: str, status: str = "active", display_name: str | None = None, session: optional[SASession] = None) -> model.User:
    """
        Create a SaaS user (seat) within a company.

        Note: Users have no email column; login email lives in auth_users.
    """
    role = (role or "").strip()
    status = (status or "").strip()
    display_name = (display_name.strip() if isinstance(display_name, str) else None)

    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if status not in VALID_USER_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_USER_STATUS)}")
    if display_name is not None and len(display_name) == 0:
        display_name = None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, int(company_id))
        if not company or company.deleted_at is not None:
            raise ValueError(f"company_id={company_id} not found or deleted.")

        subscription = session.execute(
            select(model.Subscription).where(model.Subscription.company_id == int(company_id))
        ).scalar_one_or_none()
        if not subscription:
            raise ValueError(f"company_id={company_id} does not have a subscription.")

        plan = session.get(model.SubscriptionPlan, subscription.plan_id)
        if not plan:
            raise ValueError(f"Subscription plan for company_id={company_id} not found.")

        active_user_count = session.execute(
            select(func.count()).select_from(model.User).where(
                model.User.company_id == int(company_id),
                model.User.deleted_at.is_(None),
                model.User.status == "active",
            )
        ).scalar_one()

        if status == "active" and active_user_count >= plan.seat_limit:
            raise RuntimeError(
                f"Seat limit reached for company_id={company_id}: "
                f"{active_user_count}/{plan.seat_limit} active users."
            )

        user = model.User(
            company_id=int(company_id),
            role=role,
            status=status,
            display_name=display_name,
        )

        session.add(user)
        session.flush()
        session.commit()
        session.refresh(user)
        return user

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def get_user_by_id(company_id: int,user_id: uuid.UUID,*,include_deleted: bool = False,session: optional[SASession] = None) -> optional[model.User]:
    """Fetch a user by (company_id, user_id). Returns None if not found."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User).where(
            model.User.company_id == int(company_id),
            model.User.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(model.User.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def list_users(company_id: int,*,include_deleted: bool = False,session: optional[SASession] = None) -> list[model.User]:
    """List users in a company ordered by created_at then user_id."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User).where(model.User.company_id == int(company_id))
        if not include_deleted:
            stmt = stmt.where(model.User.deleted_at.is_(None))
        stmt = stmt.order_by(model.User.created_at.asc(), model.User.user_id.asc())
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

def update_user(company_id: int,user_id: uuid.UUID,*,display_name: str | None = None,role: str | None = None,status: str | None = None,session: optional[SASession] = None) -> optional[model.User]:
    """
    Update a user's mutable fields (display_name, role, status).
    Returns updated user or None if not found (or deleted).

    Enforces company subscription seat_limit when changing a user
    from non-active to active.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.execute(
            select(model.User).where(
                model.User.company_id == int(company_id),
                model.User.user_id == user_id,
                model.User.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not user:
            return None

        if display_name is not None:
            display_name = display_name.strip()
            user.display_name = display_name if display_name else None

        if role is not None:
            role = role.strip()
            if role not in VALID_ROLES:
                raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
            user.role = role

        if status is not None:
            status = status.strip()
            if status not in VALID_USER_STATUS:
                raise ValueError(f"status must be one of {sorted(VALID_USER_STATUS)}")

            activating_user = (user.status != "active" and status == "active")

            if activating_user:
                subscription = session.execute(
                    select(model.Subscription).where(
                        model.Subscription.company_id == int(company_id)
                    )
                ).scalar_one_or_none()
                if not subscription:
                    raise ValueError(f"company_id={company_id} does not have a subscription.")

                plan = session.get(model.SubscriptionPlan, subscription.plan_id)
                if not plan:
                    raise ValueError(
                        f"Subscription plan for company_id={company_id} not found."
                    )

                active_user_count = session.execute(
                    select(func.count())
                    .select_from(model.User)
                    .where(
                        model.User.company_id == int(company_id),
                        model.User.deleted_at.is_(None),
                        model.User.status == "active",
                    )
                ).scalar_one()

                if active_user_count >= plan.seat_limit:
                    raise RuntimeError(
                        f"Seat limit reached for company_id={company_id}: "
                        f"{active_user_count}/{plan.seat_limit} active users."
                    )

            user.status = status

        session.commit()
        session.refresh(user)
        return user

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def soft_delete_user(company_id: int,user_id: uuid.UUID,*,session: optional[SASession] = None) -> bool:
    """
    Soft delete user: sets deleted_at.
    Returns True if deleted, False if not found/already deleted.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.execute(
            select(model.User).where(
                model.User.company_id == int(company_id),
                model.User.user_id == user_id,
            )
        ).scalar_one_or_none()

        if not user or user.deleted_at is not None:
            return False

        user.deleted_at = datetime.now(timezone.utc)
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def restore_user(company_id: int,user_id: uuid.UUID,*,session: optional[SASession] = None) -> bool:
    """
    Undo soft delete user: sets deleted_at NULL.
    Returns True if restored, False if not found/not deleted.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.execute(
            select(model.User).where(
                model.User.company_id == int(company_id),
                model.User.user_id == user_id,
            )
        ).scalar_one_or_none()

        if not user or user.deleted_at is None:
            return False

        user.deleted_at = None
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def hard_delete_user(company_id: int,user_id: uuid.UUID,*,session: optional[SASession] = None) -> bool:
    """
    Hard delete a user row.

    WARNING: will fail if referenced (e.g. slack_accounts, google_mailboxes, message_incidents, auth_users)
    due to FK RESTRICT.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.execute(
            select(model.User).where(
                model.User.company_id == int(company_id),
                model.User.user_id == user_id,
            )
        ).scalar_one_or_none()

        if not user:
            return False

        session.delete(user)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(
            f"DB rejected hard_delete_user (user likely still referenced): {e.orig}"
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
