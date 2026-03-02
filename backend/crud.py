from backend import alchemy_oop as model
from sqlalchemy import create_engine
from sqlalchemy import insert, delete, select, update, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_ROLE_STATUS = {"active", "inactive", "removed"}
VALID_SLACK_USER_STATUS = {"active", "inactive", "removed"}
VALID_CLASS_TYPES = {"depression", "suicide", "anxiety", "n/a"}


# ~~~~~~~~~~~~ utility functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_company_ids_by_admin_email(email: str, session: optional[SASession] = None) -> list[int]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.SaasCompanyRole.company_id)
            .join(model.SaasUserData, model.SaasUserData.user_id == model.SaasCompanyRole.user_id)
            .where(model.SaasUserData.email == email)
            .where(model.SaasCompanyRole.role == "admin")
            .where(model.SaasCompanyRole.status == "active")
        )
        return session.execute(stmt.distinct()).scalars().all()
    finally:
        if own_session:
            session.close()

def get_company_ids_by_email(
    email: str,
    *,
    only_active_role: bool = True,
    include_deleted_companies: bool = False,
    session: optional[SASession] = None,
) -> list[int]:
    """
    Returns all company_ids a user belongs to via saas_company_roles.
    """
    email = (email or "").strip()
    if not email:
        return []

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = (
            select(model.Company.company_id)
            .join(model.SaasCompanyRole, model.SaasCompanyRole.company_id == model.Company.company_id)
            .join(model.SaasUserData, model.SaasUserData.user_id == model.SaasCompanyRole.user_id)
            .where(model.SaasUserData.email == email)
        )

        if only_active_role:
            stmt = stmt.where(model.SaasCompanyRole.status == "active")
        if not include_deleted_companies:
            stmt = stmt.where(model.Company.deleted_at.is_(None))

        return session.execute(stmt.distinct()).scalars().all()
    finally:
        if own_session:
            session.close()

# ~~~~~~~~~~~~~~~~~ subscription plan ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_sub_plan(
    p_name: str,
    cost_pennies: int,
    max_employ: int,
    currency: str = "GBP",
    session: optional[SASession] = None,
) -> model.SubscriptionPlan:
    """
    Create a subscription plan.

    If `session` is provided, it will be used and NOT closed here.
    If `session` is None, this function creates/closes its own session.

    Raises:
        ValueError: invalid inputs
        RuntimeError: unique/constraint violations
    """
    p_name = (p_name or "").strip()
    currency = (currency or "GBP").strip().upper()

    if len(p_name) < 2:
        raise ValueError("plan_name must be at least 2 characters (after trimming).")
    if cost_pennies is None or int(cost_pennies) < 0:
        raise ValueError("plan_cost_pennies must be >= 0.")
    if max_employ is None or int(max_employ) <= 0:
        raise ValueError("max_employees must be > 0.")
    if len(currency) != 3:
        raise ValueError("currency must be a 3-letter code like 'GBP'.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        existing = session.execute(
            select(model.SubscriptionPlan).where(model.SubscriptionPlan.plan_name == p_name)
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Subscription plan '{p_name}' already exists (plan_id={existing.plan_id})."
            )

        plan = model.SubscriptionPlan(
            plan_name=p_name,
            plan_cost_pennies=int(cost_pennies),
            currency=currency,
            max_employees=int(max_employ),
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
        raise RuntimeError(f"DB rejected create_sub_plan: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

# ------ read all -------------
def read_all(session: optional[SASession] = None) -> list[model.SubscriptionPlan]:
    """Return all plans ordered by plan_cost_pennies then max_employees."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        return session.execute(
            select(model.SubscriptionPlan).order_by(
                model.SubscriptionPlan.plan_cost_pennies.asc(),
                model.SubscriptionPlan.max_employees.asc(),
                model.SubscriptionPlan.plan_name.asc(),
            )
        ).scalars().all()
    finally:
        if own_session:
            session.close()

# ------ get by name ----------
def get_sub_plan_by_name(p_name: str, session: optional[SASession] = None) -> optional[model.SubscriptionPlan]:
    """Get a plan by name. Returns None if not found."""
    p_name = (p_name or "").strip()

    own_session = session is None
    if own_session:
        session = Session()

    try:
        return session.execute(
            select(model.SubscriptionPlan).where(model.SubscriptionPlan.plan_name == p_name)
        ).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

# ------ update ---------------
def update_sub_plan(
    plan_id: int,
    *,
    plan_name: str | None = None,
    plan_cost_pennies: int | None = None,
    max_employees: int | None = None,
    currency: str | None = None,
    session: optional[SASession] = None,
) -> optional[model.SubscriptionPlan]:
    """
    Update a plan by id. Returns updated plan, or None if not found.
    Only updates fields you pass (others remain unchanged).
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

        if plan_cost_pennies is not None:
            if int(plan_cost_pennies) < 0:
                raise ValueError("plan_cost_pennies must be >= 0.")
            plan.plan_cost_pennies = int(plan_cost_pennies)

        if max_employees is not None:
            if int(max_employees) <= 0:
                raise ValueError("max_employees must be > 0.")
            plan.max_employees = int(max_employees)

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
        raise RuntimeError(f"DB rejected update_sub_plan: {e.orig}") from e

    except Exception:
        session.rollback()
        raise

    finally:
        if own_session:
            session.close()
   
# ------ delete ---------------
def delete_sub_plan(plan_id: int, session: optional[SASession] = None) -> bool:
    """
    Delete a plan by id.
    Returns True if deleted, False if not found.

    NOTE: Will fail if any Company rows reference the plan (FK RESTRICT).
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
        raise RuntimeError(f"DB rejected delete_sub_plan (maybe plan is in use): {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

# ~~~~~~~~~~~~~~~~ company ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_company(
    plan_id: int,
    company_name: str,
    *,
    session: optional[SASession] = None,
) -> model.Company:
    """
     create. Uses plan_id to create company .
    """
    company_name = (company_name or "").strip()
    if len(company_name) < 2:
        raise ValueError("company_name must be at least 2 characters (after trimming).")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        # Ensure plan exists firstly 
        plan = session.get(model.SubscriptionPlan, int(plan_id))
        if not plan:
            raise ValueError(f"Subscription plan id={plan_id} not found.")

        company = model.Company(plan_id=plan.plan_id, company_name=company_name)
        session.add(company)
        session.flush()  # ensures company_id
        session.commit()
        session.refresh(company)
        return company

    except ValueError:
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
 
def create_company_by_plan_name(
    plan_name: str,
    company_name: str,
    *,
    session: optional[SASession] = None,
) -> model.Company:
    """
    Convenience only for UI Team. Looks up plan_id then calls create_company(plan_id,...).
    """
    plan_name = (plan_name or "").strip()
    if len(plan_name) < 2:
        raise ValueError("plan_name must be at least 2 characters (after trimming).")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        plan = session.execute(
            select(model.SubscriptionPlan).where(model.SubscriptionPlan.plan_name == plan_name)
        ).scalar_one_or_none()
        if not plan:
            raise ValueError(f"Subscription plan '{plan_name}' not found.")

        # reuse core
        return create_company(plan.plan_id, company_name, session=session)

    finally:
        if own_session:
            session.close()

# ------ get by company --------
def get_company_by_id(
    company_id: int,
    *,
    include_deleted: bool = False,
    session: optional[SASession] = None,
) -> optional[model.Company]:
    """Fetch a company by id"""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.Company).where(model.Company.company_id == int(company_id))
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def list_companies(
    *,
    include_deleted: bool = False,
    session: optional[SASession] = None,
) -> list[model.Company]:
    
    """
    Lists all companies, optinionally those deleted aswell
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.Company)
        if not include_deleted:
            stmt = stmt.where(model.Company.deleted_at.is_(None))
        stmt = stmt.order_by(model.Company.created_at.desc(), model.Company.company_id.desc())
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

#------- update ----------------
def update_company(
    company_id: int,
    *,
    company_name: str | None = None,
    plan_id: int | None = None,
    session: optional[SASession] = None,
) -> optional[model.Company]:
    """
    updates company information like plan id or company name
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.execute(
            select(model.Company).where(
                and_(
                    model.Company.company_id == int(company_id),
                    model.Company.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not company:
            return None

        if company_name is not None:
            company_name = company_name.strip()
            if len(company_name) < 2:
                raise ValueError("company_name must be at least 2 characters (after trimming).")
            company.company_name = company_name

        if plan_id is not None:
            plan = session.get(model.SubscriptionPlan, int(plan_id))
            if not plan:
                raise ValueError(f"Subscription plan id={plan_id} not found.")
            company.plan_id = plan.plan_id

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

# ------ delete ----------------
def soft_delete_company(company_id: int, *, session: optional[SASession] = None) -> bool:
    """App delete = soft delete (sets deleted_at). for auditing purposes"""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        res = session.execute(
            update(model.Company)
            .where(and_(model.Company.company_id == int(company_id), model.Company.deleted_at.is_(None)))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        session.commit()
        return res.rowcount > 0
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

# ~~~~~~~~~~~~~~~~ saas user data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_saas_user(
    name: str,
    surname: str,
    email: str,
    password_hash: str,
    *,
    session: optional[SASession] = None,
) -> model.SaasUserData:
    """
    Create a SaaS user (unique by email).
    """
    name = (name or "").strip()
    surname = (surname or "").strip()
    email = (email or "").strip()
    password_hash = password_hash or ""

    if len(name) < 2:
        raise ValueError("name must be at least 2 characters.")
    if len(surname) < 2:
        raise ValueError("surname must be at least 2 characters.")
    if len(email) < 4 or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("email must look like a valid email.")
    if not password_hash:
        raise ValueError("password_hash must not be empty.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        existing = session.execute(
            select(model.SaasUserData).where(model.SaasUserData.email == email)
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(f"User with email '{email}' already exists (user_id={existing.user_id}).")

        user = model.SaasUserData(
            name=name,
            surname=surname,
            email=email,
            password_hash=password_hash,
        )
        session.add(user)
        session.flush()

        session.commit()
        session.refresh(user)
        return user

    except (ValueError, RuntimeError):
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_saas_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

#  ----- get user --------------
def get_user_by_id(user_id: int, *, session: optional[SASession] = None) -> optional[model.SaasUserData]:
    """returns user row via the user id """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.SaasUserData, int(user_id))
    finally:
        if own_session:
            session.close()

def get_user_by_email(email: str, *, session: optional[SASession] = None) -> optional[model.SaasUserData]:
    """returns user row or nothing, via email"""
    email = (email or "").strip()
    if not email:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.execute(
            select(model.SaasUserData).where(model.SaasUserData.email == email)
        ).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def update_user(
    user_id: int,
    *,
    name: str | None = None,
    surname: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
    session: optional[SASession] = None,
) -> optional[model.SaasUserData]:
    """
    Update user fields. Returns updated user or None if not found.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.get(model.SaasUserData, int(user_id))
        if not user:
            return None

        if name is not None:
            name = name.strip()
            if len(name) < 2:
                raise ValueError("name must be at least 2 characters.")
            user.name = name

        if surname is not None:
            surname = surname.strip()
            if len(surname) < 2:
                raise ValueError("surname must be at least 2 characters.")
            user.surname = surname

        if email is not None:
            email = email.strip()
            if len(email) < 4 or "@" not in email or email.startswith("@") or email.endswith("@"):
                raise ValueError("email must look like a valid email.")
            
            existing = session.execute(
                select(model.SaasUserData.user_id).where(
                    model.SaasUserData.email == email,
                    model.SaasUserData.user_id != int(user_id),
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise RuntimeError(f"email '{email}' is already in use by another user.")

            user.email = email

        if password_hash is not None:
            if not password_hash:
                raise ValueError("password_hash must not be empty.")
            user.password_hash = password_hash

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

#------ delete -----------------
def hard_delete_user(
    user_id: int,
    *,
    require_no_roles: bool = True,
    session: optional[SASession] = None,
) -> bool:
    """
    Hard delete user from saas_user_data.

    Safety rules:
      - If user has any ACTIVE biller role anywhere -> refuse
      - If user has any ACTIVE admin role anywhere -> refuse
      - If require_no_roles=True: refuse if ANY role rows exist (even inactive/removed)
        (because FK RESTRICT will also block if roles exist)

    Returns:
      True if deleted, False if not found.

    Raises:
      RuntimeError if deletion is not allowed due to billing/admin/roles.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        user = session.get(model.SaasUserData, int(user_id))
        if not user:
            return False

        # Blocking if active biller anywhere
        active_biller = session.execute(
            select(model.SaasCompanyRole.company_id).where(
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == "biller",
                model.SaasCompanyRole.status == "active",
            ).limit(1)
        ).scalar_one_or_none()
        if active_biller is not None:
            raise RuntimeError("Cannot delete user: user is an ACTIVE biller for at least one company.")

        # Blocking if active admin anywhere
        active_admin = session.execute(
            select(model.SaasCompanyRole.company_id).where(
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == "admin",
                model.SaasCompanyRole.status == "active",
            ).limit(1)
        ).scalar_one_or_none()
        if active_admin is not None:
            raise RuntimeError("Cannot delete user: user is an ACTIVE admin for at least one company.")

        # If its later decided stricly no role rows at all
        if require_no_roles:
            any_roles = session.execute(
                select(model.SaasCompanyRole.company_id).where(
                    model.SaasCompanyRole.user_id == int(user_id)
                ).limit(1)
            ).scalar_one_or_none()
            if any_roles is not None:
                raise RuntimeError(
                    "Cannot delete user: user still has company role rows "
                    "Remove memberships first (set roles to 'removed'), then delete."
                )

        session.delete(user)
        session.commit()
        return True

    except RuntimeError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()

        raise RuntimeError(f"DB rejected hard_delete_user (user still referenced): {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ~~~~~~~~~~~~~~~~ saas company role ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#######  CONSIDER LOCKING ROWS FOR CONCURRENCY ###########


def generic_upsert_company_role(
    company_id: int,
    user_id: int,
    role: str,
    status: str = "active",
    *,
    session: optional[SASession] = None,
) -> model.SaasCompanyRole:
    """
    Upsert a NON-CRITICAL role row (e.g. viewer).
    Use set_company_admin / set_company_biller for admin/biller roles.
    """
    role = (role or "").strip()
    status = (status or "").strip()

    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if role in {"admin", "biller"}:
        raise ValueError("Use set_company_admin / set_company_biller for admin/biller roles.")
    if status not in VALID_ROLE_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_ROLE_STATUS)}")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")
        if not session.get(model.SaasUserData, int(user_id)):
            raise ValueError(f"user_id={user_id} not found.")

        existing = session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == role,
            )
        ).scalar_one_or_none()

        if existing:
            existing.status = status
            session.commit()
            session.refresh(existing)
            return existing

        row = model.SaasCompanyRole(
            company_id=int(company_id),
            user_id=int(user_id),
            role=role,
            status=status,
        )
        session.add(row)
        session.flush()
        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected upsert_company_role: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

#------- update ----------------
def set_company_biller(company_id: int, user_id: int, *, session: optional[SASession] = None) -> model.SaasCompanyRole:
    """
    Makes user_id the active biller for company_id.
    Safe ordering:
      1) ensure new biller is active (insert/update)
      2) flush so DB sees an active biller exists
      3) demote previous active biller(s)
    """
    own = session is None
    if own:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")
        if not session.get(model.SaasUserData, int(user_id)):
            raise ValueError(f"user_id={user_id} not found.")
        
        #demoting first
        session.execute(
            update(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .where(model.SaasCompanyRole.role == "biller")
            .where(model.SaasCompanyRole.status == "active")
            .where(model.SaasCompanyRole.user_id != int(user_id))
            .values(status="inactive")
        )

        row = session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == "biller",
            )
        ).scalar_one_or_none()

        if row is None:
            row = model.SaasCompanyRole(
                company_id=int(company_id),
                user_id=int(user_id),
                role="biller",
                status="active",
            )
            session.add(row)
        else:
            row.status = "active"

        session.flush() 

        session.commit()
        session.refresh(row)
        return row

    except (ValueError, RuntimeError):
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected set_company_biller: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def set_company_admin(company_id: int, user_id: int, *, session: optional[SASession] = None) -> model.SaasCompanyRole:
    own = session is None
    if own:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")
        if not session.get(model.SaasUserData, int(user_id)):
            raise ValueError(f"user_id={user_id} not found.")

        # demote any currently-active admin 
        session.execute(
            update(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .where(model.SaasCompanyRole.role == "admin")
            .where(model.SaasCompanyRole.status == "active")
            .where(model.SaasCompanyRole.user_id != int(user_id))
            .values(status="inactive")
        )

        # upsert this user admin row as active
        row = session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == "admin",
            )
        ).scalar_one_or_none()

        if row is None:
            row = model.SaasCompanyRole(
                company_id=int(company_id),
                user_id=int(user_id),
                role="admin",
                status="active",
            )
            session.add(row)
        else:
            row.status = "active"

        session.commit()
        session.refresh(row)
        return row

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected set_company_admin: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

#  ----- get user roles --------------
def get_company_roles(company_id: int, *, session: optional[SASession] = None) -> list[model.SaasCompanyRole]:
    """Return all role rows for a company."""
    own = session is None
    if own:
        session = Session()
    try:
        rows = session.execute(
            select(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .order_by(model.SaasCompanyRole.role, model.SaasCompanyRole.user_id)
        ).scalars().all()
        return list(rows)
    finally:
        if own:
            session.close()

def get_user_roles_in_company(company_id: int, user_id: int, *, session: optional[SASession] = None) -> list[model.SaasCompanyRole]:
    """Return all roles for a user within a company."""
    own = session is None
    if own:
        session = Session()
    try:
        rows = session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.user_id == int(user_id),
            )
        ).scalars().all()
        return list(rows)
    finally:
        if own:
            session.close()

def has_role(company_id: int, user_id: int, role: str, *, status: optional[str] = None, session: optional[SASession] = None) -> bool:
    """Check if a role row exists, optionally filtered by status."""
    role = (role or "").strip()
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")

    if status is not None:
        status = (status or "").strip()
        if status not in VALID_ROLE_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_ROLE_STATUS)}")

    own = session is None
    if own:
        session = Session()
    try:
        stmt = select(model.SaasCompanyRole.company_id).where(
            model.SaasCompanyRole.company_id == int(company_id),
            model.SaasCompanyRole.user_id == int(user_id),
            model.SaasCompanyRole.role == role,
        )
        if status is not None:
            stmt = stmt.where(model.SaasCompanyRole.status == status)

        return session.execute(stmt).first() is not None
    finally:
        if own:
            session.close()

def get_active_admin(company_id: int, *, session: optional[SASession] = None) -> optional[model.SaasCompanyRole]:
    own = session is None
    if own:
        session = Session()
    try:
        return session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.role == "admin",
                model.SaasCompanyRole.status == "active",
            )
        ).scalar_one_or_none()
    finally:
        if own:
            session.close()

def get_active_biller(company_id: int, *, session: optional[SASession] = None) -> optional[model.SaasCompanyRole]:
    own = session is None
    if own:
        session = Session()
    try:
        return session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.role == "biller",
                model.SaasCompanyRole.status == "active",
            )
        ).scalar_one_or_none()
    finally:
        if own:
            session.close()

# ------soft delete ----------------
def remove_role(company_id: int, user_id: int, role: str, *, session: optional[SASession] = None) -> None:
    """
    Generic soft-remove: sets status='removed'.
    Disallows admin/biller because triggers will often block removals.
    """
    role = (role or "").strip()
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if role in {"admin", "biller"}:
        raise ValueError("Use transfer/rotate logic (set_company_admin/biller) before removing admin/biller.")

    own = session is None
    if own:
        session = Session()

    try:
        session.execute(
            update(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .where(model.SaasCompanyRole.user_id == int(user_id))
            .where(model.SaasCompanyRole.role == role)
            .values(status="removed")
        )
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected remove_role: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()


# ~~~~~~~~~~~~~~~~ slack workspace ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_workspace(
    company_id: int,
    team_id: str,
    access_token: str,
    *,
    session: optional[SASession] = None,
) -> model.Workspace:
    """
    Register a Slack workspace for a company.

    Constraints:
      - company_id must exist
      - team_id is unique
      - access_token required
    """
    team_id = (team_id or "").strip()
    access_token = (access_token or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not access_token:
        raise ValueError("access_token is required")

    own = session is None
    if own:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")

        row = model.Workspace(
            company_id=int(company_id),
            team_id=team_id,
            access_token=access_token,
        )
        session.add(row)
        session.flush() 
        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        # could be a duplicate team_id, or FK failure
        raise RuntimeError(f"DB rejected create_workspace: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def get_workspace_by_id(workspace_id: int, *, session: optional[SASession] = None) -> optional[model.Workspace]:
    own = session is None
    if own:
        session = Session()
    try:
        return session.get(model.Workspace, int(workspace_id))
    finally:
        if own:
            session.close()

def get_workspace_by_team_id(team_id: str, *, session: optional[SASession] = None) -> optional[model.Workspace]:
    team_id = (team_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")

    own = session is None
    if own:
        session = Session()
    try:
        return session.execute(
            select(model.Workspace).where(model.Workspace.team_id == team_id)
        ).scalar_one_or_none()
    finally:
        if own:
            session.close()

def list_workspaces_for_company(company_id: int, *, session: optional[SASession] = None) -> list[model.Workspace]:
    own = session is None
    if own:
        session = Session()
    try:
        rows = session.execute(
            select(model.Workspace)
            .where(model.Workspace.company_id == int(company_id))
            .order_by(model.Workspace.id)
        ).scalars().all()
        return list(rows)
    finally:
        if own:
            session.close()

def update_workspace_access_token(
    team_id: str,
    new_access_token: str,
    *,
    session: optional[SASession] = None,
) -> model.Workspace:
    """
    Rotate/update a workspace access token by team_id.
    Returns updated row. Raises ValueError if not found.
    """
    team_id = (team_id or "").strip()
    new_access_token = (new_access_token or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not new_access_token:
        raise ValueError("new_access_token is required")

    own = session is None
    if own:
        session = Session()

    try:
        ws = session.execute(
            select(model.Workspace).where(model.Workspace.team_id == team_id)
        ).scalar_one_or_none()
        if ws is None:
            raise ValueError(f"workspace team_id={team_id} not found.")

        ws.access_token = new_access_token
        session.commit()
        session.refresh(ws)
        return ws

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_workspace_access_token: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def upsert_workspace_by_team_id(
    company_id: int,
    team_id: str,
    access_token: str,
    *,
    session: optional[SASession] = None,
) -> model.Workspace:
    """
    If workspace exists (by team_id), update company_id + access_token.
    Else create it.
    """
    team_id = (team_id or "").strip()
    access_token = (access_token or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not access_token:
        raise ValueError("access_token is required")

    own = session is None
    if own:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")

        ws = session.execute(
            select(model.Workspace).where(model.Workspace.team_id == team_id)
        ).scalar_one_or_none()

        if ws is None:
            ws = model.Workspace(company_id=int(company_id), team_id=team_id, access_token=access_token)
            session.add(ws)
            session.flush()
        else:
            ws.company_id = int(company_id)
            ws.access_token = access_token

        session.commit()
        session.refresh(ws)
        return ws

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected upsert_workspace_by_team_id: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def delete_workspace_by_team_id(team_id: str, *, session: optional[SASession] = None) -> None:
    """
    Hard delete a workspace row.
    Note: may be blocked by FK constraints (e.g. slack_users rows referencing team_id).
    """
    team_id = (team_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")

    own = session is None
    if own:
        session = Session()

    try:
        result = session.execute(
            delete(model.Workspace).where(model.Workspace.team_id == team_id)
        )
        if result.rowcount == 0:
            raise ValueError(f"workspace team_id={team_id} not found.")

        session.commit()

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected delete_workspace_by_team_id (FK constraint?): {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()


# ~~~~~~~~~~~~~~~ slack users ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_slack_user(
    team_id: str,
    slack_user_id: str,
    name: str,
    surname: str,
    status: str = "active",
    *,
    session: optional[SASession] = None,
) -> model.SlackUser:
    """
    Insert a slack user row.

    DB constraints:
      - (team_id, slack_user_id) must be unique
      - team_id must exist in slack_workspaces (FK, RESTRICT)
      - name/surname length > 1 (after trim)
      - status in ('active','inactive','removed')
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    name = (name or "").strip()
    surname = (surname or "").strip()
    status = (status or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")
    if len(name) <= 1:
        raise ValueError("name must be > 1 char")
    if len(surname) <= 1:
        raise ValueError("surname must be > 1 char")
    if status not in VALID_SLACK_USER_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_SLACK_USER_STATUS)}")

    own = session is None
    if own:
        session = Session()

    try:
        # ensure workspace 
        ws = session.execute(select(model.Workspace).where(model.Workspace.team_id == team_id)).scalar_one_or_none()
        if ws is None:
            raise ValueError(f"workspace team_id={team_id} not found.")

        row = model.SlackUser(
            team_id=team_id,
            slack_user_id=slack_user_id,
            name=name,
            surname=surname,
            status=status,
        )
        session.add(row)
        session.flush()
        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_slack_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def get_slack_user_by_id(slack_user_db_id: int, *, session: optional[SASession] = None) -> optional[model.SlackUser]:
    """returns slack user by id """
    own = session is None
    if own:
        session = Session()
    try:
        return session.get(model.SlackUser, int(slack_user_db_id))
    finally:
        if own:
            session.close()

def get_slack_user_by_team_and_slack_id(
    team_id: str,
    slack_user_id: str,
    *,
    session: optional[SASession] = None,
) -> optional[model.SlackUser]:
    """returns slack user by team and slack id """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")

    own = session is None
    if own:
        session = Session()
    try:
        return session.execute(
            select(model.SlackUser).where(
                model.SlackUser.team_id == team_id,
                model.SlackUser.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
    finally:
        if own:
            session.close()

def list_slack_users_for_workspace(
    team_id: str,
    *,
    status: optional[str] = None,
    session: optional[SASession] = None,
) -> list[model.SlackUser]:
    """List all users withibn a workspace"""
    team_id = (team_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")
    if status is not None:
        status = (status or "").strip()
        if status not in VALID_SLACK_USER_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_SLACK_USER_STATUS)}")

    own = session is None
    if own:
        session = Session()
    try:
        stmt = (
            select(model.SlackUser)
            .where(model.SlackUser.team_id == team_id)
            .order_by(model.SlackUser.id)
        )
        if status is not None:
            stmt = stmt.where(model.SlackUser.status == status)

        rows = session.execute(stmt).scalars().all()
        return list(rows)
    finally:
        if own:
            session.close()

def update_slack_user_profile(
    team_id: str,
    slack_user_id: str,
    *,
    name: optional[str] = None,
    surname: optional[str] = None,
    session: optional[SASession] = None,
) -> model.SlackUser:
    """
    Update name/surname for a slack user 
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")

    if name is None and surname is None:
        raise ValueError("Provide at least one of name or surname to update.")

    if name is not None:
        name = (name or "").strip()
        if len(name) <= 1:
            raise ValueError("name must be > 1 char")
    if surname is not None:
        surname = (surname or "").strip()
        if len(surname) <= 1:
            raise ValueError("surname must be > 1 char")

    own = session is None
    if own:
        session = Session()

    try:
        row = session.execute(
            select(model.SlackUser).where(
                model.SlackUser.team_id == team_id,
                model.SlackUser.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"slack user not found team_id={team_id} slack_user_id={slack_user_id}")

        if name is not None:
            row.name = name
        if surname is not None:
            row.surname = surname

        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_slack_user_profile: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def set_slack_user_status(
    team_id: str,
    slack_user_id: str,
    status: str,
    *,
    session: optional[SASession] = None,
) -> model.SlackUser:
    """
    Set status to active/inactive/removed (soft delete = removed).
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    status = (status or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")
    if status not in VALID_SLACK_USER_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_SLACK_USER_STATUS)}")

    own = session is None
    if own:
        session = Session()

    try:
        row = session.execute(
            select(model.SlackUser).where(
                model.SlackUser.team_id == team_id,
                model.SlackUser.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"slack user not found team_id={team_id} slack_user_id={slack_user_id}")

        row.status = status
        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected set_slack_user_status: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def upsert_slack_user(
    team_id: str,
    slack_user_id: str,
    name: str,
    surname: str,
    status: str = "active",
    *,
    session: optional[SASession] = None,
) -> model.SlackUser:
    """
    Insert if missing (team_id, slack_user_id), else update name/surname/status.
    Useful when syncing from Slack API.
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    name = (name or "").strip()
    surname = (surname or "").strip()
    status = (status or "").strip()

    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")
    if len(name) <= 1:
        raise ValueError("name must be > 1 char")
    if len(surname) <= 1:
        raise ValueError("surname must be > 1 char")
    if status not in VALID_SLACK_USER_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_SLACK_USER_STATUS)}")

    own = session is None
    if own:
        session = Session()

    try:
        # ensure workspace exists
        ws = session.execute(select(model.Workspace).where(model.Workspace.team_id == team_id)).scalar_one_or_none()
        if ws is None:
            raise ValueError(f"workspace team_id={team_id} not found.")

        row = session.execute(
            select(model.SlackUser).where(
                model.SlackUser.team_id == team_id,
                model.SlackUser.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()

        if row is None:
            row = model.SlackUser(
                team_id=team_id,
                slack_user_id=slack_user_id,
                name=name,
                surname=surname,
                status=status,
            )
            session.add(row)
            session.flush()
        else:
            row.name = name
            row.surname = surname
            row.status = status

        session.commit()
        session.refresh(row)
        return row

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected upsert_slack_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()

def hard_delete_slack_user(
    team_id: str,
    slack_user_id: str,
    *,
    session: optional[SASession] = None,
) -> None:
    """
    Hard delete a slack user row by natural key.
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required")
    if not slack_user_id:
        raise ValueError("slack_user_id is required")

    own = session is None
    if own:
        session = Session()

    try:
        result = session.execute(
            delete(model.SlackUser).where(
                model.SlackUser.team_id == team_id,
                model.SlackUser.slack_user_id == slack_user_id,
            )
        )
        if result.rowcount == 0:
            raise ValueError(f"slack user not found team_id={team_id} slack_user_id={slack_user_id}")

        session.commit()

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected delete_slack_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()


# ~~~~~~~~~~~~~~~ Flagged Incident ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_flagged_incident(
    *,
    company_id: int,
    team_id: str,
    slack_user_id: str,
    message_ts: str,
    channel_id: str,
    raw_message_text: dict,
    class_reason: str | None = None,
    session: optional[SASession] = None,
) -> model.FlaggedIncident:
    """
    Create a flagged incident.
    Notes:
      - DB enforces FK(team_id)->slack_workspaces(team_id)
      - DB enforces composite FK(team_id, slack_user_id)->slack_users(team_id, slack_user_id)
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    message_ts = (message_ts or "").strip()
    channel_id = (channel_id or "").strip()

    if not company_id or int(company_id) <= 0:
        raise ValueError("company_id must be a positive integer.")
    if not team_id:
        raise ValueError("team_id is required.")
    if not slack_user_id:
        raise ValueError("slack_user_id is required.")
    if not message_ts:
        raise ValueError("message_ts is required.")
    if not channel_id:
        raise ValueError("channel_id is required.")
    if raw_message_text is None or not isinstance(raw_message_text, dict):
        raise ValueError("raw_message_text must be a dict (JSON serializable).")


    own_session = session is None
    if own_session:
        session = Session()

    try:
        incident = model.FlaggedIncident(
            company_id=int(company_id),
            team_id=team_id,
            slack_user_id=slack_user_id,
            message_ts=message_ts,
            channel_id=channel_id,
            raw_message_text=raw_message_text,
            class_reason=class_reason,
        )

        session.add(incident)
        session.flush()
        session.commit()
        session.refresh(incident)
        return incident

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_flagged_incident: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def read_all_flagged_incidents(
    *,
    company_id: int | None = None,
    team_id: str | None = None,
    slack_user_id: str | None = None,
    limit: int = 200,
    offset: int = 0,
    newest_first: bool = True,
    session: optional[SASession] = None,
) -> list[model.FlaggedIncident]:
    """
    Read incidents with optional filters.
    Default ordering: newest first.
    """
    if limit is None or int(limit) <= 0 or int(limit) > 5000:
        raise ValueError("limit must be between 1 and 5000.")
    if offset is None or int(offset) < 0:
        raise ValueError("offset must be >= 0.")

    team_id = team_id.strip() if team_id else None
    slack_user_id = slack_user_id.strip() if slack_user_id else None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.FlaggedIncident)

        if company_id is not None:
            stmt = stmt.where(model.FlaggedIncident.company_id == int(company_id))
        if team_id is not None:
            stmt = stmt.where(model.FlaggedIncident.team_id == team_id)
        if slack_user_id is not None:
            stmt = stmt.where(model.FlaggedIncident.slack_user_id == slack_user_id)

        if newest_first:
            stmt = stmt.order_by(
                model.FlaggedIncident.created_at.desc(),
                model.FlaggedIncident.incident_id.desc())
        else:
            stmt = stmt.order_by(
                model.FlaggedIncident.created_at.asc(),
                model.FlaggedIncident.incident_id.asc())

        stmt = stmt.limit(int(limit)).offset(int(offset))

        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

#might need to delete it by some other means instead of id 
def delete_flagged_incident(
    *,
    incident_id: int,
    session: optional[SASession] = None,
) -> bool:
    """
    Hard delete by PK.
    Returns True if deleted, False if not found.
    """
    if incident_id is None or int(incident_id) <= 0:
        raise ValueError("incident_id must be a positive integer.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        incident = session.get(model.FlaggedIncident, int(incident_id))
        if not incident:
            return False

        session.delete(incident)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected delete_flagged_incident: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def count_flagged_incidents(
    *,
    company_id: int | None = None,
    team_id: str | None = None,
    slack_user_id: str | None = None,
    session: optional[SASession] = None,
) -> int:
    """
    for  UI: "total results".
    """
    team_id = team_id.strip() if team_id else None
    slack_user_id = slack_user_id.strip() if slack_user_id else None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.FlaggedIncident.incident_id)

        if company_id is not None:
            stmt = stmt.where(model.FlaggedIncident.company_id == int(company_id))
        if team_id is not None:
            stmt = stmt.where(model.FlaggedIncident.team_id == team_id)
        if slack_user_id is not None:
            stmt = stmt.where(model.FlaggedIncident.slack_user_id == slack_user_id)

        ids = session.execute(stmt).scalars().all()
        return len(ids)
    finally:
        if own_session:
            session.close()

#this can be used for both company analytics and for saas users
def get_flagged_incidents_by_class_types(
    *,
    class_types: set[str] | list[str] | tuple[str, ...],
    company_id: int | None = None,
    team_id: str | None = None,
    slack_user_id: str | None = None,
    include_unclassified: bool = False,
    limit: int = 200,
    offset: int = 0,
    newest_first: bool = True,
    session: optional[SASession] = None,
) -> list[model.FlaggedIncident]:
    """
    Fetch incidents filtered by one or more class_reason "types".

    - class_types: e.g. {"depression", "suicide"}
    - include_unclassified: if True, also includes rows where class_reason IS NULL
    - Optional filters: company_id, team_id, slack_user_id
    """
    if not class_types:
        raise ValueError("class_types must not be empty.")
    if limit is None or int(limit) <= 0 or int(limit) > 5000:
        raise ValueError("limit must be between 1 and 5000.")
    if offset is None or int(offset) < 0:
        raise ValueError("offset must be >= 0.")

    # Normalize incoming types
    normalized = {str(t).strip().lower() for t in class_types if str(t).strip()}
    if not normalized:
        raise ValueError("class_types must contain at least one non-empty value.")

    unknown = normalized - VALID_CLASS_TYPES
    if unknown:
        raise ValueError(f"Unknown class_types: {sorted(unknown)}. Allowed: {sorted(VALID_CLASS_TYPES)}")

    team_id = team_id.strip() if team_id else None
    slack_user_id = slack_user_id.strip() if slack_user_id else None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.FlaggedIncident)

        # base filters
        if company_id is not None:
            stmt = stmt.where(model.FlaggedIncident.company_id == int(company_id))
        if team_id is not None:
            stmt = stmt.where(model.FlaggedIncident.team_id == team_id)
        if slack_user_id is not None:
            stmt = stmt.where(model.FlaggedIncident.slack_user_id == slack_user_id)

        # type filters
        type_filter = model.FlaggedIncident.class_reason.in_(list(normalized))
        if include_unclassified:
            stmt = stmt.where(
                model.FlaggedIncident.class_reason.is_(None) | type_filter
            )
        else:
            stmt = stmt.where(type_filter)

        # ordering + pagination
        stmt = stmt.order_by(
            model.FlaggedIncident.created_at.desc()
            if newest_first
            else model.FlaggedIncident.created_at.asc()
        ).limit(int(limit)).offset(int(offset))

        return session.execute(stmt).scalars().all()

    finally:
        if own_session:
            session.close()

def get_most_recent_incident(
    *,
    company_id: int | None = None,
    team_id: str | None = None,
    slack_user_id: str | None = None,
    class_types: set[str] | list[str] | tuple[str, ...] | None = None,
    include_unclassified: bool = False,
    session: optional[SASession] = None,
) -> model.FlaggedIncident | None:
    """
    Returns the most recent (by created_at) flagged incident, optionally filtered.

    Filters:
      - company_id, team_id, slack_user_id
      - class_types: iterable of class_reason values (e.g. {"suicide","anxiety"})
      - include_unclassified: if True and class_types provided, also allow class_reason IS NULL
    """
    team_id = team_id.strip() if team_id else None
    slack_user_id = slack_user_id.strip() if slack_user_id else None

    if class_types is not None:
        normalized = {str(t).strip().lower() for t in class_types if str(t).strip()}
        if not normalized:
            raise ValueError("class_types was provided but contained no valid values.")
        # If you defined VALID_CLASS_TYPES earlier, validate here:
        unknown = normalized - VALID_CLASS_TYPES
        if unknown:
            raise ValueError(f"Unknown class_types: {sorted(unknown)}. Allowed: {sorted(VALID_CLASS_TYPES)}")
    else:
        normalized = None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = select(model.FlaggedIncident)

        if company_id is not None:
            if int(company_id) <= 0:
                raise ValueError("company_id must be a positive integer.")
            stmt = stmt.where(model.FlaggedIncident.company_id == int(company_id))

        if team_id is not None:
            stmt = stmt.where(model.FlaggedIncident.team_id == team_id)

        if slack_user_id is not None:
            stmt = stmt.where(model.FlaggedIncident.slack_user_id == slack_user_id)

        if normalized is not None:
            type_filter = model.FlaggedIncident.class_reason.in_(list(normalized))
            if include_unclassified:
                stmt = stmt.where(model.FlaggedIncident.class_reason.is_(None) | type_filter)
            else:
                stmt = stmt.where(type_filter)

        stmt = stmt.order_by(
                model.FlaggedIncident.created_at.desc(),
                model.FlaggedIncident.incident_id.desc(),
            ).limit(1)

        return session.execute(stmt).scalars().first()

    finally:
        if own_session:
            session.close()

