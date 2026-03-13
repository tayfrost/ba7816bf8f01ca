
"""
DB Service

!!!!other teams please read this
Monitored employees do not need to be pre-registered. 
When a new identity is first seen (via a Gmail OAuth connect or an incoming Slack message), a
canonical viewer seat is auto-created in the users table
But currently linking a person's slack and email is impossible since there's no shared employee_id
that we're expecting client to provide us


Read from DATABASE_URL env var so the same code works everywhere:
  Local:          postgresql+psycopg://postgres:postgres@localhost:5432/sentinelai
  Docker Compose: postgresql+psycopg://postgres:postgres@db:5432/sentinelai
  Production:     postgresql+psycopg://user:pass@<private-host>:5432/sentinelai
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session as SASession
from sqlalchemy.exc import IntegrityError

from backend.New_database import new_oop as model

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


#returns a user id string
def ensure_viewer_seat(company_id: int, email_address: str, display_name: Optional[str] = None,*, session: Optional[SASession] = None,) -> str:
    user_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"user:{company_id}:{email_address.lower()}",
    )
    own_session = session is None
    if own_session:
        session = Session()
    try:
        existing = session.execute(
            select(model.User).where(
                model.User.company_id == company_id,
                model.User.user_id == user_uuid,
            )
        ).scalar_one_or_none()

        if not existing:
            session.add(model.User(
                user_id=user_uuid,
                company_id=company_id,
                display_name=display_name or email_address,
                role="viewer",
                status="active",
            ))
            session.commit()
            logger.info(
                f"[DB] Auto-created viewer seat for {email_address} "
                f"company={company_id} user_id={user_uuid}"
            )
        else:
            logger.debug(
                f"[DB] Viewer seat already exists for {email_address} "
                f"user_id={user_uuid}"
            )
        return str(user_uuid)

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected ensure_viewer_seat: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ── gmail ──────────────────────────────────────────────

def create_gmail_account(company_id: int,user_id: str,email_address: str,token_json: str,*,session: Optional[SASession] = None,) -> model.GoogleMailbox:
    """
    Upsert a google_mailboxes row.
    as mentioned in top comment overview, the viewer seat for this user_id must already exist before calling this
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        mailbox = session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.company_id == company_id,
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()

        if mailbox:
            mailbox.token_json = token_json
            mailbox.user_id = uuid.UUID(user_id)
            logger.info(f"[DB] Refreshed token for mailbox {email_address}")
        else:
            mailbox = model.GoogleMailbox(
                company_id=company_id,
                user_id=uuid.UUID(user_id),
                email_address=email_address,
                token_json=token_json,
            )
            session.add(mailbox)
            logger.info(f"[DB] Created google_mailboxes row for {email_address}")

        session.commit()
        session.refresh(mailbox)
        return mailbox

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_gmail_account: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_gmail_account_by_email(email_address: str,*,session: Optional[SASession] = None,) -> Optional[model.GoogleMailbox]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


def update_gmail_history_id(email_address: str,last_history_id: str,*,session: Optional[SASession] = None,) -> None:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        mailbox = session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()
        if not mailbox:
            logger.warning(
                f"[DB] update_gmail_history_id: no mailbox for {email_address}"
            )
            return
        mailbox.last_history_id = last_history_id
        session.commit()
        logger.info(f"[DB] history_id updated for {email_address} → {last_history_id}")
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def update_gmail_watch(
    email_address: str,
    last_history_id: str,
    watch_expiration: datetime,
    *,
    session: Optional[SASession] = None,
) -> None:
    """Store the historyId and watch expiry returned by Gmail watch()."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        mailbox = session.execute(
            select(model.GoogleMailbox).where(
                model.GoogleMailbox.email_address == email_address,
            )
        ).scalar_one_or_none()
        if not mailbox:
            logger.warning(f"[DB] update_gmail_watch: no mailbox for {email_address}")
            return
        mailbox.last_history_id = last_history_id
        mailbox.watch_expiration = watch_expiration
        session.commit()
        logger.info(f"[DB] Watch updated for {email_address} expires={watch_expiration}")
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def list_gmail_accounts(
    *,
    session: Optional[SASession] = None,
) -> list[model.GoogleMailbox]:
    """Return all google_mailboxes rows (used by watch-renewal cron)."""
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return list(session.execute(select(model.GoogleMailbox)).scalars().all())
    finally:
        if own_session:
            session.close()


# ──slack──────────────────────────────────────────────

def upsert_workspace_by_team_id(
    company_id: int,
    team_id: str,
    access_token: str,
    *,
    session: Optional[SASession] = None,
) -> model.SlackWorkspace:
    """
    Insert-or-update a slack_workspaces row.
    Re-installing the same workspace clears revoked_at and refreshes the token.
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        workspace = session.execute(
            select(model.SlackWorkspace).where(
                model.SlackWorkspace.team_id == team_id,
            )
        ).scalar_one_or_none()

        if workspace:
            workspace.access_token = access_token
            workspace.revoked_at = None
            logger.info(f"[DB] Updated slack_workspace team={team_id}")
        else:
            workspace = model.SlackWorkspace(
                company_id=company_id,
                team_id=team_id,
                access_token=access_token,
            )
            session.add(workspace)
            logger.info(f"[DB] Created slack_workspace team={team_id}")

        session.commit()
        session.refresh(workspace)
        return workspace

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected upsert_workspace: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def get_workspace_by_team_id(
    team_id: str,
    *,
    session: Optional[SASession] = None,
) -> Optional[model.SlackWorkspace]:
    """
    Fetch an active (non-revoked) slack_workspaces row.
    Returns None if not found or revoked.
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.execute(
            select(model.SlackWorkspace).where(
                model.SlackWorkspace.team_id == team_id,
                model.SlackWorkspace.revoked_at.is_(None),
            )
        ).scalar_one_or_none()
    finally:
        if own_session:
            session.close()


# ── Slack Accounts ────────────────────────────────────────────────

def upsert_slack_account(
    company_id: int,
    team_id: str,
    slack_user_id: str,
    user_id: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    *,
    session: Optional[SASession] = None,
) -> None:
    """
    Insert-or-update a slack_accounts row (PK: team_id, slack_user_id).
    Same as mentioned for gmail
    The viewer seat for this user_id must already exist before calling this.
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        user_uuid = uuid.UUID(user_id)

        account = session.execute(
            select(model.SlackAccount).where(
                model.SlackAccount.team_id == team_id,
                model.SlackAccount.slack_user_id == slack_user_id,
            )
        ).scalar_one_or_none()

        if account:
            if email is not None:
                account.email = email
        else:
            session.add(model.SlackAccount(
                company_id=company_id,
                team_id=team_id,
                slack_user_id=slack_user_id,
                user_id=user_uuid,
                email=email,
            ))

        session.commit()
        logger.info(
            f"[DB] Upserted slack_account slack_user={slack_user_id} team={team_id}"
        )

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected upsert_slack_account: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


# ── Message Incidents ─────────────────────────────────────────────

def create_flagged_incident(
    *,
    company_id: int,
    user_id: str,
    source: str,
    sent_at: datetime,
    content_raw: dict,
    conversation_id: Optional[str] = None,
    session: Optional[SASession] = None,
) -> str:
    """
    Insert a row into message_incidents.
    Returns the new message_id (UUID string).
    """
    if source not in ("slack", "gmail"):
        raise ValueError(f"Invalid source: {source!r}. Must be 'slack' or 'gmail'.")

    own_session = session is None
    if own_session:
        session = Session()
    try:
        message_id = uuid.uuid4()
        session.add(model.MessageIncident(
            message_id=message_id,
            company_id=company_id,
            user_id=uuid.UUID(user_id),
            source=source,
            sent_at=sent_at,
            content_raw=content_raw,
            conversation_id=conversation_id,
        ))
        session.commit()
        logger.info(
            f"[DB] Incident created id={message_id} source={source} "
            f"company={company_id} user={user_id}"
        )
        return str(message_id)

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_flagged_incident: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def create_incident_scores(
    *,
    message_id: str,
    neutral_score: float = 0.0,
    humor_sarcasm_score: float = 0.0,
    stress_score: float = 0.0,
    burnout_score: float = 0.0,
    depression_score: float = 0.0,
    harassment_score: float = 0.0,
    suicidal_ideation_score: float = 0.0,
    predicted_category: Optional[str] = None,
    predicted_severity: Optional[int] = None,
    session: Optional[SASession] = None,
) -> None:
    """
    Insert a row into incident_scores (1:1 with message_incidents).
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        session.add(model.IncidentScore(
            message_id=uuid.UUID(message_id),
            neutral_score=neutral_score,
            humor_sarcasm_score=humor_sarcasm_score,
            stress_score=stress_score,
            burnout_score=burnout_score,
            depression_score=depression_score,
            harassment_score=harassment_score,
            suicidal_ideation_score=suicidal_ideation_score,
            predicted_category=predicted_category,
            predicted_severity=predicted_severity,
        ))
        session.commit()
        logger.info(f"[DB] Scores stored for incident {message_id}")

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_incident_scores: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()