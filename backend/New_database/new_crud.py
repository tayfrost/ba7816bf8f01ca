from backend.New_database import new_oop as model
from sqlalchemy import select, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid


engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

# ~~~~~~~~~~~~ utility functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def get_company_id_by_name(name: str,*,include_deleted: bool = False,session: optional[SASession] = None) -> optional[int]:
    """
        Provide name of company, will return the company id
    """
    
    name = (name or "").strip()
    if not name:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.company_id).where(model.Company.name == name)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_company_name_by_id(company_id: int,*,session: optional[SASession] = None) -> optional[str]:
    """"provide company id,
        returns company name """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.name).where(model.Company.company_id == company_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def company_exists(company_id: int,*,include_deleted: bool = False,session: optional[SASession] = None) -> bool:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company.company_id).where(model.Company.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def user_exists(company_id: int,user_id,*,include_deleted: bool = False,session: optional[SASession] = None) -> bool:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
        )
        if not include_deleted:
            stmt = stmt.where(model.User.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def is_company_admin(company_id: int,user_id,*,must_be_active_user: bool = True,session: optional[SASession] = None) -> bool:
    """
    Checks if user is an admin within the company.
    role/status is on users table
    can also check inactive admins via must_be_active_user = False
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
            model.User.role == "admin",
        )
        if must_be_active_user:
            stmt = stmt.where(
                model.User.status == "active",
                model.User.deleted_at.is_(None),
            )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def require_company_admin(company_id: int,user_id,*,session: optional[SASession] = None) -> None:
    """
    Convenience guard: raises ValueError if not admin.
    """
    if not is_company_admin(company_id, user_id, session=session):
        raise ValueError("User is not an active admin for this company.")

def is_company_member(company_id: int,user_id,*,must_be_active_user: bool = True,session: optional[SASession] = None) -> bool:
    """
        can also check if non active admin member via must_be_active_user = False
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.User.user_id).where(
            model.User.company_id == company_id,
            model.User.user_id == user_id,
        )
        if must_be_active_user:
            stmt = stmt.where(
                model.User.status == "active",
                model.User.deleted_at.is_(None),
            )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def get_google_mailbox_id_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> optional[int]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox.google_mailbox_id)
            .where(
                model.GoogleMailbox.company_id == company_id,
                model.GoogleMailbox.user_id == user_id,
            )
            .order_by(model.GoogleMailbox.google_mailbox_id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_google_email_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> optional[str]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox.email_address)
            .where(
                model.GoogleMailbox.company_id == company_id,
                model.GoogleMailbox.user_id == user_id,
            )
            .order_by(model.GoogleMailbox.google_mailbox_id.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_slack_identity_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> list[tuple[str, str]]:
    """
    Returns list of (team_id, slack_user_id) linked to this user.
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackAccount.team_id, model.SlackAccount.slack_user_id).where(
            model.SlackAccount.company_id == company_id,
            model.SlackAccount.user_id == user_id,
        )
        return list(session.execute(stmt).all())
    finally:
        if own_session:
            session.close()

def get_slack_workspace_id_by_team_id(team_id: str,*,session: optional[SASession] = None) -> optional[int]:
    team_id = (team_id or "").strip()
    if not team_id:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace.slack_workspace_id).where(model.SlackWorkspace.team_id == team_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def slack_workspace_active(team_id: str,*,session: optional[SASession] = None) -> bool:
    """
    Active means installed and not revoked.
    """
    team_id = (team_id or "").strip()
    if not team_id:
        return False

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace.team_id).where(
            model.SlackWorkspace.team_id == team_id,
            model.SlackWorkspace.revoked_at.is_(None),
        )
        return session.execute(stmt).scalar_one_or_none() is not None
    finally:
        if own_session:
            session.close()

def google_mailbox_active_for_user(company_id: int,user_id,*,session: optional[SASession] = None) -> bool:
    """
     goole_mailboxes table will treat 'exists' as active.
     later decision may add revoked_at, update this to check it
    """
    return get_google_mailbox_id_for_user(company_id, user_id, session=session) is not None

def validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {sorted(VALID_ROLES)}")

def validate_user_status(status: str) -> None:
    if status not in VALID_USER_STATUS:
        raise ValueError(f"Invalid status: {status}. Must be one of {sorted(VALID_USER_STATUS)}")


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




# ====================== COMPANIES TABLE =======================
def create_company(name: str,*,session: optional[SASession] = None) -> model.Company:
    """
    Create a company (soft-delete supported via deleted_at).

    Raises:
        ValueError: invalid inputs
        RuntimeError: unique/constraint violations
    """
    name = (name or "").strip()
    if len(name) < 2:
        raise ValueError("company name must be at least 2 characters (after trimming).")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        # if a deleted company exists with same name, treated as conflict
        existing = session.execute(
            select(model.Company).where(model.Company.name == name)
        ).scalar_one_or_none()
        if existing:
            if existing.deleted_at is None:
                raise RuntimeError(f"Company '{name}' already exists (company_id={existing.company_id}).")
            raise RuntimeError(
                f"Company '{name}' exists but is deleted (company_id={existing.company_id}). "
                f"Use restore_company(company_id=...) instead."
            )

        company = model.Company(name=name)
        session.add(company)
        session.flush() 
        session.commit()
        session.refresh(company)
        return company

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_company: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def get_company_by_id(company_id: int,*,include_deleted: bool = False,session: optional[SASession] = None) -> optional[model.Company]:
    """Fetch a company by id. Returns None if not found."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company).where(model.Company.company_id == company_id)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def get_company_by_name(name: str,*,include_deleted: bool = False,session: optional[SASession] = None) -> optional[model.Company]:
    """Fetch a company by name. Returns None if not found."""
    name = (name or "").strip()
    if not name:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company).where(model.Company.name == name)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def list_companies(*,include_deleted: bool = False,session: optional[SASession] = None) -> list[model.Company]:
    """List companies ordered by created_at then name."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        stmt = stmt.order_by(model.Company.created_at.asc(), model.Company.name.asc())
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

def update_company(company_id: int,*,name: str | None = None,session: optional[SASession] = None) -> optional[model.Company]:
    """
    Update mutable company fields ( only name).
    Returns updated company or None if not found (or deleted).
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, company_id)
        if not company or company.deleted_at is not None:
            return None

        if name is not None:
            name = name.strip()
            if len(name) < 2:
                raise ValueError("company name must be at least 2 characters (after trimming).")
            company.name = name

        session.commit()
        session.refresh(company)
        return company

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_company: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def soft_delete_company(company_id: int,*,session: optional[SASession] = None) -> bool:
    """
    Soft delete a company by setting deleted_at.
    Returns True if soft-deleted, False if not found or already deleted.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, company_id)
        if not company or company.deleted_at is not None:
            return False

        company.deleted_at = datetime.now(timezone.utc)
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def restore_company(company_id: int,*,session: optional[SASession] = None) -> bool:
    """
    Undo soft delete (sets deleted_at NULL).
    Returns True if restored, False if not found or not deleted.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, company_id)
        if not company or company.deleted_at is None:
            return False

        company.deleted_at = None
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def hard_delete_company(company_id: int,*,session: optional[SASession] = None) -> bool:
    """
    Hard delete the company row.
    WARNING: This will fail if any child rows exist due to FK RESTRICT
             (subscriptions, users, slack_workspaces, google_mailboxes, auth_users, message_incidents).
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, company_id)
        if not company:
            return False

        session.delete(company)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(
            f"DB rejected hard_delete_company (company likely still referenced): {e.orig}"
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()



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


# =============================  USERS TABLE ======================
def create_user(company_id: int,*,role: str,status: str = "active",display_name: str | None = None,session: optional[SASession] = None) -> model.User:
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
            user.status = status

        session.commit()
        session.refresh(user)
        return user

    except ValueError:
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








