from database.new_database import new_oop as model
from database.new_database.utils.utility_functions import (
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


VALID_SOURCES = {"slack", "gmail"}


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


# ====================== SLACK ACCOUNTS =========================

def create_slack_account(
    company_id: int,
    *,
    team_id: str,
    slack_user_id: str,
    user_id: uuid.UUID,
    email: str | None = None,
    session: optional[SASession] = None,
) -> model.SlackAccount:
    """
    Link a Slack user identity to a SaaS user seat.

    PK is (team_id, slack_user_id).
    Composite FKs enforce that the team and user both belong to the same company.

    Raises:
        ValueError: invalid inputs or missing parent rows
        RuntimeError: constraint violations
    """
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    email = (email.strip() if isinstance(email, str) else None)

    if not team_id:
        raise ValueError("team_id is required.")
    if not slack_user_id:
        raise ValueError("slack_user_id is required.")
    if user_id is None:
        raise ValueError("user_id is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not company_exists(company_id, session=session):
            raise ValueError(f"company_id={company_id} not found or deleted.")
        if not user_exists(company_id, user_id, session=session):
            raise ValueError(f"user_id={user_id} not found in company_id={company_id}.")

        ws = session.execute(
            select(model.SlackWorkspace).where(
                model.SlackWorkspace.company_id == int(company_id),
                model.SlackWorkspace.team_id == team_id,
            )
        ).scalar_one_or_none()
        if not ws:
            raise ValueError(
                f"No slack workspace with team_id='{team_id}' for company_id={company_id}."
            )
        if ws.revoked_at is not None:
            raise ValueError(
                f"Slack workspace team_id='{team_id}' is revoked for company_id={company_id}."
            )

        existing = session.execute(
            select(model.SlackAccount).where(
                model.SlackAccount.team_id == team_id,
                model.SlackAccount.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Slack account ({team_id}, {slack_user_id}) already exists."
            )

        acct = model.SlackAccount(
            company_id=int(company_id),
            team_id=team_id,
            slack_user_id=slack_user_id,
            user_id=user_id,
            email=email if email else None,
        )
        session.add(acct)
        session.flush()
        session.commit()
        session.refresh(acct)
        return acct

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_slack_account: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_slack_account(
    team_id: str,
    slack_user_id: str,
    *,
    session: optional[SASession] = None,
) -> optional[model.SlackAccount]:
    """Fetch by composite PK (team_id, slack_user_id)."""
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id or not slack_user_id:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackAccount).where(
            model.SlackAccount.team_id == team_id,
            model.SlackAccount.slack_user_id == slack_user_id,
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def list_slack_accounts_for_company(
    company_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.SlackAccount]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.SlackAccount)
            .where(model.SlackAccount.company_id == int(company_id))
            .order_by(model.SlackAccount.team_id.asc(), model.SlackAccount.slack_user_id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def list_slack_accounts_for_user(
    company_id: int,
    user_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.SlackAccount]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = (
            select(model.SlackAccount)
            .where(
                model.SlackAccount.company_id == int(company_id),
                model.SlackAccount.user_id == user_id,
            )
            .order_by(model.SlackAccount.team_id.asc(), model.SlackAccount.slack_user_id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def update_slack_account_email(
    team_id: str,
    slack_user_id: str,
    *,
    email: str | None,
    session: optional[SASession] = None,
) -> optional[model.SlackAccount]:
    """Update the email metadata on a slack account. Returns None if not found."""
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id or not slack_user_id:
        return None

    own_session = session is None
    if own_session:
        session = Session()

    try:
        acct = session.execute(
            select(model.SlackAccount).where(
                model.SlackAccount.team_id == team_id,
                model.SlackAccount.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
        if not acct:
            return None

        acct.email = email.strip() if isinstance(email, str) and email.strip() else None
        session.commit()
        session.refresh(acct)
        return acct

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_slack_account_email: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def hard_delete_slack_account(
    team_id: str,
    slack_user_id: str,
    *,
    session: optional[SASession] = None,
) -> bool:
    """Hard delete a slack account. Returns True if deleted, False if not found."""
    team_id = (team_id or "").strip()
    slack_user_id = (slack_user_id or "").strip()
    if not team_id or not slack_user_id:
        raise ValueError("team_id and slack_user_id are required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        acct = session.execute(
            select(model.SlackAccount).where(
                model.SlackAccount.team_id == team_id,
                model.SlackAccount.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()
        if not acct:
            return False

        session.delete(acct)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected hard_delete_slack_account: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ====================== GOOGLE MAILBOXES =========================

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


# ====================== AUTH USERS ================================

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


# ====================== MESSAGE INCIDENTS =========================

def create_message_incident(
    company_id: int,
    *,
    user_id: uuid.UUID,
    source: str,
    sent_at: datetime,
    content_raw: dict,
    conversation_id: str | None = None,
    session: optional[SASession] = None,
) -> model.MessageIncident:
    """
    Create a flagged message incident (from Slack or Gmail).

    Raises:
        ValueError: invalid inputs or missing parent rows
        RuntimeError: constraint violations
    """
    source = (source or "").strip().lower()
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
    if user_id is None:
        raise ValueError("user_id is required.")
    if sent_at is None:
        raise ValueError("sent_at is required.")
    if content_raw is None:
        raise ValueError("content_raw is required.")
    if not isinstance(content_raw, dict):
        raise ValueError("content_raw must be a dict.")

    conversation_id = (conversation_id.strip() if isinstance(conversation_id, str) else None)

    own_session = session is None
    if own_session:
        session = Session()

    try:
        if not company_exists(company_id, session=session):
            raise ValueError(f"company_id={company_id} not found or deleted.")
        if not user_exists(company_id, user_id, session=session):
            raise ValueError(f"user_id={user_id} not found in company_id={company_id}.")

        incident = model.MessageIncident(
            company_id=int(company_id),
            user_id=user_id,
            source=source,
            sent_at=sent_at,
            content_raw=content_raw,
            conversation_id=conversation_id if conversation_id else None,
        )
        session.add(incident)
        session.flush()
        session.commit()
        session.refresh(incident)
        return incident

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_message_incident: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_message_incident_by_id(
    message_id: uuid.UUID,
    *,
    session: optional[SASession] = None,
) -> optional[model.MessageIncident]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.MessageIncident, message_id)
    finally:
        if own_session:
            session.close()


def list_message_incidents_for_company(
    company_id: int,
    *,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.MessageIncident]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.MessageIncident).where(
            model.MessageIncident.company_id == int(company_id)
        )
        if source is not None:
            source = source.strip().lower()
            if source not in VALID_SOURCES:
                raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
            stmt = stmt.where(model.MessageIncident.source == source)
        stmt = stmt.order_by(model.MessageIncident.sent_at.desc()).limit(limit).offset(offset)
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def list_message_incidents_for_user(
    company_id: int,
    user_id: uuid.UUID,
    *,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: optional[SASession] = None,
) -> list[model.MessageIncident]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.MessageIncident).where(
            model.MessageIncident.company_id == int(company_id),
            model.MessageIncident.user_id == user_id,
        )
        if source is not None:
            source = source.strip().lower()
            if source not in VALID_SOURCES:
                raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
            stmt = stmt.where(model.MessageIncident.source == source)
        stmt = stmt.order_by(model.MessageIncident.sent_at.desc()).limit(limit).offset(offset)
        return list(session.execute(stmt).scalars().all())
    finally:
        if own_session:
            session.close()


def hard_delete_message_incident(
    message_id: uuid.UUID,
    *,
    session: optional[SASession] = None,
) -> bool:
    """
    Hard delete a message incident.
    incident_scores CASCADE-deletes automatically.
    Returns True if deleted, False if not found.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        incident = session.get(model.MessageIncident, message_id)
        if not incident:
            return False

        session.delete(incident)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected hard_delete_message_incident: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ====================== INCIDENT SCORES ==========================

def create_incident_scores(
    message_id: uuid.UUID,
    *,
    neutral_score: float,
    humor_sarcasm_score: float,
    stress_score: float,
    burnout_score: float,
    depression_score: float,
    harassment_score: float,
    suicidal_ideation_score: float,
    predicted_category: str | None = None,
    predicted_severity: int | None = None,
    session: optional[SASession] = None,
) -> model.IncidentScores:
    """
    Create ML scores for a message incident (1:1 relationship).

    UNIQUE(message_id) — one score row per incident.
    FK ON DELETE CASCADE — deleting the incident auto-deletes scores.

    Raises:
        ValueError: invalid inputs or missing incident
        RuntimeError: constraint violations
    """
    if message_id is None:
        raise ValueError("message_id is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        incident = session.get(model.MessageIncident, message_id)
        if not incident:
            raise ValueError(f"message_id={message_id} not found.")

        existing = session.execute(
            select(model.IncidentScores).where(model.IncidentScores.message_id == message_id)
        ).scalar_one_or_none()
        if existing:
            raise RuntimeError(
                f"Scores already exist for message_id={message_id} (id={existing.id})."
            )

        parsed_severity = None
        if predicted_severity is not None:
            try:
                parsed_severity = int(predicted_severity)
            except (ValueError, TypeError):
                raise ValueError("predicted_severity must be an integer.")

        scores = model.IncidentScores(
            message_id=message_id,
            neutral_score=float(neutral_score),
            humor_sarcasm_score=float(humor_sarcasm_score),
            stress_score=float(stress_score),
            burnout_score=float(burnout_score),
            depression_score=float(depression_score),
            harassment_score=float(harassment_score),
            suicidal_ideation_score=float(suicidal_ideation_score),
            predicted_category=predicted_category.strip() if isinstance(predicted_category, str) else None,
            predicted_severity=parsed_severity,
        )
        session.add(scores)
        session.flush()
        session.commit()
        session.refresh(scores)
        return scores

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_incident_scores: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_incident_scores_by_message_id(
    message_id: uuid.UUID,
    *,
    session: optional[SASession] = None,
) -> optional[model.IncidentScores]:
    """Fetch scores for a message incident. Returns None if not scored yet."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.IncidentScores).where(model.IncidentScores.message_id == message_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def get_incident_scores_by_id(
    scores_id: int,
    *,
    session: optional[SASession] = None,
) -> optional[model.IncidentScores]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.IncidentScores, int(scores_id))
    finally:
        if own_session:
            session.close()


def update_incident_scores(
    message_id: uuid.UUID,
    *,
    neutral_score: float | None = None,
    humor_sarcasm_score: float | None = None,
    stress_score: float | None = None,
    burnout_score: float | None = None,
    depression_score: float | None = None,
    harassment_score: float | None = None,
    suicidal_ideation_score: float | None = None,
    predicted_category: str | None = ...,
    predicted_severity: int | None = ...,
    session: optional[SASession] = None,
) -> optional[model.IncidentScores]:
    """
    Update existing scores for a message incident.
    Only updates fields you pass; others stay unchanged.
    Use None explicitly for predicted_category/predicted_severity to clear them.
    Returns None if scores row not found.
    """
    own_session = session is None
    if own_session:
        session = Session()

    try:
        scores = session.execute(
            select(model.IncidentScores).where(model.IncidentScores.message_id == message_id)
        ).scalar_one_or_none()
        if not scores:
            return None

        if neutral_score is not None:
            scores.neutral_score = float(neutral_score)
        if humor_sarcasm_score is not None:
            scores.humor_sarcasm_score = float(humor_sarcasm_score)
        if stress_score is not None:
            scores.stress_score = float(stress_score)
        if burnout_score is not None:
            scores.burnout_score = float(burnout_score)
        if depression_score is not None:
            scores.depression_score = float(depression_score)
        if harassment_score is not None:
            scores.harassment_score = float(harassment_score)
        if suicidal_ideation_score is not None:
            scores.suicidal_ideation_score = float(suicidal_ideation_score)
        if predicted_category is not ...:
            scores.predicted_category = predicted_category.strip() if isinstance(predicted_category, str) and predicted_category.strip() else None
        if predicted_severity is not ...:
            if predicted_severity is not None:
                try:
                    scores.predicted_severity = int(predicted_severity)
                except (ValueError, TypeError):
                    raise ValueError("predicted_severity must be an integer.")
            else:
                scores.predicted_severity = None

        session.commit()
        session.refresh(scores)
        return scores

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_incident_scores: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def hard_delete_incident_scores(
    message_id: uuid.UUID,
    *,
    session: optional[SASession] = None,
) -> bool:
    """Hard delete scores for a message incident. Returns True if deleted, False if not found."""
    own_session = session is None
    if own_session:
        session = Session()

    try:
        scores = session.execute(
            select(model.IncidentScores).where(model.IncidentScores.message_id == message_id)
        ).scalar_one_or_none()
        if not scores:
            return False

        session.delete(scores)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected hard_delete_incident_scores: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
