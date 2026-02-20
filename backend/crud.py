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


# ---------------- read all ----------------
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


# ---------------- get by name ----------------
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


# ---------------- update ----------------
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
   

# ---------------- delete ----------------
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

# ---------------- get by company ----------------
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

# ------------------update -------------------
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

# ----------------- delete -------------
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
    
def hard_delete_company(company_id: int, *, session: optional[SASession] = None) -> bool:
    """
    Hard delete: DELETE FROM companies.
    Returns True if deleted, False if not found.

    NOTE: Will fail if other tables reference this company,
    e.g. saas_company_roles, slack_workspaces.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, int(company_id))
        if not company:
            return False

        session.delete(company)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected hard_delete_company (company referenced elsewhere): {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

# ~~~~~~~~~~~~~~~~ saas user data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_saas_data(name, surname, email, hashed_pass):
    pass
# ~~~~~~~~~~~~~~~~ saas company role ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_saas_roles(role, status, company_id, company_name):
    pass
# ~~~~~~~~~~~~~~~~ slack workspace ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_workspace(company_id, comapny_id):
    pass
# ~~~~~~~~~~~~~~~ slack tracker ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~~~~



