from database.database import new_oop as model
from database.db_service.utils.utility_functions import (
    Session,
    company_exists,
    user_exists,
)
from sqlalchemy import select
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError
import uuid


def create_auth_user(
    company_id: int,
    *,
    email: str,
    password_hash: str,
    user_id: uuid.UUID | None = None,
    session: optional[SASession] = None,
) -> model.AuthUser:
    """
    Create a login account (auth_user) for a company.

    email is UNIQUE globally (CITEXT).
    user_id optionally links to a users seat.

    Raises:
        ValueError: invalid inputs or missing parent rows
        RuntimeError: constraint violations
    """
    email = (email or "").strip()
    password_hash = (password_hash or "").strip()

    if not email:
        raise ValueError("email is required.")
    if not password_hash:
        raise ValueError("password_hash is required.")
    if len(password_hash) < 20:
        raise ValueError("password_hash looks too short — did you pass a plaintext password?")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not company_exists(company_id, session=session):
            raise ValueError(f"company_id={company_id} not found or deleted.")

        if user_id is not None:
            if not user_exists(company_id, user_id, session=session):
                raise ValueError(f"user_id={user_id} not found in company_id={company_id}.")

        existing = session.execute(
            select(model.AuthUser).where(model.AuthUser.email == email)
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Auth user with email '{email}' already exists (auth_user_id={existing.auth_user_id})."
            )

        au = model.AuthUser(
            company_id=int(company_id),
            user_id=user_id,
            email=email,
            password_hash=password_hash,
        )
        session.add(au)
        session.flush()
        session.commit()
        session.refresh(au)
        return au

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_auth_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_auth_user_by_id(
    auth_user_id: int,
    *,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.AuthUser, int(auth_user_id))
    finally:
        if own_session:
            session.close()


def get_auth_user_by_email(
    email: str,
    *,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    """Lookup by login email (case-insensitive via CITEXT)."""
    email = (email or "").strip()
    if not email:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.AuthUser).where(model.AuthUser.email == email)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def get_auth_user_by_user_id(
    company_id: int,
    user_id: uuid.UUID,
    *,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    """Lookup the auth (login) account linked to a SaaS user seat."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.AuthUser).where(
            model.AuthUser.company_id == int(company_id),
            model.AuthUser.user_id == user_id,
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def list_auth_users_for_company(
    company_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.AuthUser]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.AuthUser)
            .where(model.AuthUser.company_id == int(company_id))
            .order_by(model.AuthUser.created_at.asc(), model.AuthUser.auth_user_id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def update_auth_user_password(
    auth_user_id: int,
    *,
    password_hash: str,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    """Update password hash. Returns None if not found."""
    password_hash = (password_hash or "").strip()
    if not password_hash:
        raise ValueError("password_hash is required.")
    if len(password_hash) < 20:
        raise ValueError("password_hash looks too short — did you pass a plaintext password?")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        au = session.get(model.AuthUser, int(auth_user_id))
        if not au:
            return None

        au.password_hash = password_hash
        session.commit()
        session.refresh(au)
        return au

    except ValueError:
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def update_auth_user_email(
    auth_user_id: int,
    *,
    new_email: str,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    """Update login email (CITEXT, globally unique). Returns None if not found."""
    new_email = (new_email or "").strip()
    if not new_email:
        raise ValueError("new_email is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        au = session.get(model.AuthUser, int(auth_user_id))
        if not au:
            return None

        au.email = new_email
        session.commit()
        session.refresh(au)
        return au

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_auth_user_email (likely duplicate): {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def update_auth_user_link(
    auth_user_id: int,
    *,
    user_id: uuid.UUID | None,
    session: optional[SASession] = None,
) -> optional[model.AuthUser]:
    """Link or unlink an auth_user to/from a users seat. Returns None if not found."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        au = session.get(model.AuthUser, int(auth_user_id))
        if not au:
            return None

        if user_id is not None:
            if not user_exists(au.company_id, user_id, session=session):
                raise ValueError(
                    f"user_id={user_id} not found in company_id={au.company_id}."
                )

        au.user_id = user_id
        session.commit()
        session.refresh(au)
        return au

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_auth_user_link: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def hard_delete_auth_user(
    auth_user_id: int,
    *,
    session: optional[SASession] = None,
) -> bool:
    """Hard delete an auth user. Returns True if deleted, False if not found."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        au = session.get(model.AuthUser, int(auth_user_id))
        if not au:
            return False

        session.delete(au)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected hard_delete_auth_user: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
