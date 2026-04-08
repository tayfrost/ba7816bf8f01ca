from database.database import models as model
from database.services.utility_functions import Session
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
import uuid


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


def list_daily_score_averages(
    company_id: int,
    start_dt: datetime,
    end_dt: datetime,
    *,
    session: optional[SASession] = None,
) -> list[dict]:
    """
    Return daily average scores per employee, then averaged across employees.

    Two-level aggregation:
      1. Inner: per (day, user_id) — average each score column so every
         employee contributes equally regardless of message volume.
      2. Outer: per day — average those per-employee averages across all
         employees active that day.

    Returns a list of dicts with keys:
        day (date), depression, burnout, stress, harassment, suicidal_ideation
    """
    own_session = session is None
    if own_session:
        session = Session()
    try:
        MI = model.MessageIncident
        IS = model.IncidentScores
        day_col = cast(MI.sent_at, Date).label("day")

        # Inner subquery: per-employee daily averages
        per_user = (
            select(
                day_col,
                MI.user_id,
                func.avg(IS.depression_score).label("depression"),
                func.avg(IS.burnout_score).label("burnout"),
                func.avg(IS.stress_score).label("stress"),
                func.avg(IS.harassment_score).label("harassment"),
                func.avg(IS.suicidal_ideation_score).label("suicidal_ideation"),
            )
            .join(IS, IS.message_id == MI.message_id)
            .where(
                MI.company_id == int(company_id),
                MI.sent_at >= start_dt,
                MI.sent_at <= end_dt,
            )
            .group_by(day_col, MI.user_id)
            .subquery()
        )

        # Outer: average per-employee values across all employees per day
        stmt = (
            select(
                per_user.c.day,
                func.avg(per_user.c.depression).label("depression"),
                func.avg(per_user.c.burnout).label("burnout"),
                func.avg(per_user.c.stress).label("stress"),
                func.avg(per_user.c.harassment).label("harassment"),
                func.avg(per_user.c.suicidal_ideation).label("suicidal_ideation"),
            )
            .group_by(per_user.c.day)
            .order_by(per_user.c.day)
        )

        rows = session.execute(stmt).all()
        return [
            {
                "day": row.day,
                "depression": float(row.depression or 0),
                "burnout": float(row.burnout or 0),
                "stress": float(row.stress or 0),
                "harassment": float(row.harassment or 0),
                "suicidal_ideation": float(row.suicidal_ideation or 0),
            }
            for row in rows
        ]
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
