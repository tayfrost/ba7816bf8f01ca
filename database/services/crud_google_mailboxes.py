from database.database import models as model
from database.services.utility_functions import (
    Session,
    company_exists,
    user_exists,
)
from sqlalchemy import select
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError
import uuid


def _increment_history_id(current: str | None) -> str:
    """Increment a text-stored history counter by one.
    Raises ValueError if current contains a non-numeric string."""
    if current is None:
        return "1"
    try:
        return str(int(current) + 1)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"last_history_id must be a numeric string, got: {current!r}"
        ) from e


def create_google_mailbox(
    company_id: int,
    *,
    user_id: uuid.UUID,
    email_address: str,
    token_json: dict,
    last_history_id: str | None = None,
    watch_expiration: datetime | None = None,
    session: optional[SASession] = None,
) -> model.GoogleMailbox:
    """
    Connect a Gmail mailbox for a user.

    UNIQUE(company_id, email_address) — one mailbox email per company.
    last_history_id is stored as TEXT and incremented manually.

    Raises:
        ValueError: invalid inputs or missing parent rows
        RuntimeError: constraint violations
    """
    email_address = (email_address or "").strip()
    if not email_address:
        raise ValueError("email_address is required.")
    if user_id is None:
        raise ValueError("user_id is required.")
    if token_json is None:
        raise ValueError("token_json is required.")
    if last_history_id is not None:
        try:
            int(last_history_id)
        except (ValueError, TypeError):
            raise ValueError(f"last_history_id must be a numeric string, got: {last_history_id!r}")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not company_exists(company_id, session=session):
            raise ValueError(f"company_id={company_id} not found or deleted.")
        if not user_exists(company_id, user_id, session=session):
            raise ValueError(f"user_id={user_id} not found in company_id={company_id}.")

        existing = session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.company_id == int(company_id),
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Google mailbox '{email_address}' already exists for company_id={company_id} "
                f"(google_mailbox_id={existing.google_mailbox_id})."
            )

        mb = model.GoogleMailbox(
            company_id=int(company_id),
            user_id=user_id,
            email_address=email_address,
            token_json=token_json,
            last_history_id=last_history_id,
            watch_expiration=watch_expiration,
        )
        session.add(mb)
        session.flush()
        session.commit()
        session.refresh(mb)
        return mb

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_google_mailbox: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_google_mailbox_by_id(
    google_mailbox_id: int,
    *,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.GoogleMailbox, int(google_mailbox_id))
    finally:
        if own_session:
            session.close()


def list_google_mailboxes_for_company(
    company_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.GoogleMailbox]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox)
            .where(model.GoogleMailbox.company_id == int(company_id))
            .order_by(model.GoogleMailbox.google_mailbox_id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def list_google_mailboxes_for_user(
    company_id: int,
    user_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.GoogleMailbox]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.GoogleMailbox)
            .where(
                model.GoogleMailbox.company_id == int(company_id),
                model.GoogleMailbox.user_id == user_id,
            )
            .order_by(model.GoogleMailbox.google_mailbox_id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def get_google_mailbox_by_email(
    company_id: int,
    email_address: str,
    *,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    """Lookup a mailbox by its unique email within a company.
    Useful for webhook routing during Gmail sync."""
    email_address = (email_address or "").strip()
    if not email_address:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.GoogleMailbox).where(
            model.GoogleMailbox.company_id == int(company_id),
            model.GoogleMailbox.email_address == email_address,
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def update_google_mailbox_token(
    google_mailbox_id: int,
    *,
    token_json: dict,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    """Update OAuth token JSON. Returns None if not found."""
    if token_json is None:
        raise ValueError("token_json is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        mb = session.get(model.GoogleMailbox, int(google_mailbox_id))
        if not mb:
            return None

        mb.token_json = token_json
        session.commit()
        session.refresh(mb)
        return mb

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_google_mailbox_token: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def increment_google_mailbox_history_id(
    google_mailbox_id: int,
    *,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    """
    Increment last_history_id by one (stored as TEXT).
    If currently NULL, sets to "1".
    Uses SELECT ... FOR UPDATE to prevent concurrent workers
    from reading the same value and overwriting each other.
    Returns updated mailbox or None if not found.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        stmt = (
            select(model.GoogleMailbox)
            .where(model.GoogleMailbox.google_mailbox_id == int(google_mailbox_id))
            .with_for_update()
        )
        mb = session.execute(stmt).scalar_one_or_none()
        if not mb:
            return None

        mb.last_history_id = _increment_history_id(mb.last_history_id)
        session.commit()
        session.refresh(mb)
        return mb

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def set_google_mailbox_history_id(
    google_mailbox_id: int,
    *,
    last_history_id: str | None,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    """Directly set last_history_id (TEXT). Must be a numeric string or None."""
    if last_history_id is not None:
        try:
            int(last_history_id)
        except (ValueError, TypeError):
            raise ValueError(f"last_history_id must be a numeric string, got: {last_history_id!r}")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        mb = session.get(model.GoogleMailbox, int(google_mailbox_id))
        if not mb:
            return None

        mb.last_history_id = last_history_id
        session.commit()
        session.refresh(mb)
        return mb

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def update_google_mailbox_watch_expiration(
    google_mailbox_id: int,
    *,
    watch_expiration: datetime | None,
    session: optional[SASession] = None,
) -> optional[model.GoogleMailbox]:
    """Update watch expiration timestamp. Returns None if not found."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        mb = session.get(model.GoogleMailbox, int(google_mailbox_id))
        if not mb:
            return None

        mb.watch_expiration = watch_expiration
        session.commit()
        session.refresh(mb)
        return mb

    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def hard_delete_google_mailbox(
    google_mailbox_id: int,
    *,
    session: optional[SASession] = None,
) -> bool:
    """Hard delete a google mailbox. Returns True if deleted, False if not found."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        mb = session.get(model.GoogleMailbox, int(google_mailbox_id))
        if not mb:
            return False

        session.delete(mb)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(
            f"DB rejected hard_delete_google_mailbox: {e.orig}"
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
