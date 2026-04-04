from database.database import new_oop as model
from database.db_service.utils.utility_functions import (
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


def create_message_incident(
    company_id: int,
    *,
    user_id: uuid.UUID,
    source: str,
    sent_at: datetime,
    content_raw: dict,
    conversation_id: str | None = None,
    recommendation: str | None = None,
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
    recommendation = (recommendation.strip() if isinstance(recommendation, str) else None)

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
            recommendation=recommendation if recommendation else None,
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
