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

#------- update ----------------
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
##Potential delete
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

def set_company_biller(company_id: int, user_id: int, *, session: optional[SASession] = None) -> None:
    """
    Makes user_id the active biller for company_id.
    Order matters:
      1) ensure new biller is active
      2) demote previous active biller(s)
    triggers:
      - uq_one_active_biller_per_company
      - prevent_last_active_biller_removal trigger
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")
        if not session.get(model.SaasUserData, int(user_id)):
            raise ValueError(f"user_id={user_id} not found.")

        # (company_id,user_id,'biller') exists + set active
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

        #  Demote any other active biller
        session.execute(
            update(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .where(model.SaasCompanyRole.role == "biller")
            .where(model.SaasCompanyRole.status == "active")
            .where(model.SaasCompanyRole.user_id != int(user_id))
            .values(status="inactive")
        )

        session.commit()

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
        if own_session:
            session.close()
#------- update ----------------
def set_company_admin(
    company_id: int,
    user_id: int,
    *,
    session: optional[SASession] = None,
) -> None:
    """
    Makes user_id the ONLY active admin for company_id.
    ensuring partial uniqueness.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        
        if not session.get(model.Company, int(company_id)):
            raise ValueError(f"company_id={company_id} not found.")
        if not session.get(model.SaasUserData, int(user_id)):
            raise ValueError(f"user_id={user_id} not found.")

        # deactivate existing active admin(s) to switch admins
        session.execute(
            update(model.SaasCompanyRole)
            .where(model.SaasCompanyRole.company_id == int(company_id))
            .where(model.SaasCompanyRole.role == "admin")
            .where(model.SaasCompanyRole.status == "active")
            .values(status="inactive")
        )

        # upsert admin row for this user, incase user was deactivated before
        row = session.execute(
            select(model.SaasCompanyRole).where(
                model.SaasCompanyRole.company_id == int(company_id),
                model.SaasCompanyRole.user_id == int(user_id),
                model.SaasCompanyRole.role == "admin",
            )
        ).scalar_one_or_none()

        # creating new role, in case where user wasnt admin before hand
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

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected set_company_admin: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ~~~~~~~~~~~~~~~~ slack workspace ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_workspace(company_id, comapny_id):
    pass
# ~~~~~~~~~~~~~~~ slack tracker ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~



