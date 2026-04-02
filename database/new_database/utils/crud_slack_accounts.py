from database.new_database import new_oop as model
from database.new_database.utils.utility_functions import (
    Session,
    company_exists,
    user_exists,
)
from sqlalchemy import select
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError
import uuid


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
