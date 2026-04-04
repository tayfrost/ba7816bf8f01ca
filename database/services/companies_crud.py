from database.database import new_oop as model
from sqlalchemy import select, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from database.db_service.utils import utility_functions as ufunc
import uuid

engine = create_engine("postgresql+psycopg://postgres:postgres@pgvector:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

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
