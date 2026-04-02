from database.new_database import new_oop as model
from sqlalchemy import select, and_
from datetime import datetime, timezone
from sqlalchemy.orm import Session as SASession
from typing import Optional as optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from database.new_database.utils import utility_functions as ufunc
import uuid

engine = create_engine("postgresql+psycopg://postgres:postgres@pgvector:5432/sentinelai", echo=True)
Session = sessionmaker(bind=engine)

VALID_ROLES = {"admin", "viewer", "biller"}
VALID_USER_STATUS = {"active", "inactive"}
VALID_SUBSCRIPTION_STATUS = {"trialing", "active", "past_due", "canceled"}

# =============================  SLACK WORKSPACES =====================

def create_slack_workspace(company_id: int,*,team_id: str,access_token: str,session: optional[SASession] = None) -> model.SlackWorkspace:
    """
    Create/install a Slack workspace for a company.

    Constraints:
      - team_id is UNIQUE globally (one workspace per Slack team across all companies)
      - (company_id, team_id) is also unique
    """
    team_id = (team_id or "").strip()
    access_token = (access_token or "").strip()

    if not team_id:
        raise ValueError("team_id is required.")
    if not access_token:
        raise ValueError("access_token is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        company = session.get(model.Company, int(company_id))
        if not company or company.deleted_at is not None:
            raise ValueError(f"company_id={company_id} not found or deleted.")

        existing = session.execute(
            select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        ).scalar_one_or_none()
        if existing:
            if existing.revoked_at is not None:
                raise RuntimeError(
                    f"Slack team_id='{team_id}' exists but is revoked "
                    f"(slack_workspace_id={existing.slack_workspace_id}). "
                    f"Use reinstall_slack_workspace(team_id=...) to update token and clear revoked_at."
                )
            raise RuntimeError(
                f"Slack team_id='{team_id}' already installed (slack_workspace_id={existing.slack_workspace_id})."
            )

        ws = model.SlackWorkspace(
            company_id=int(company_id),
            team_id=team_id,
            access_token=access_token,
        )
        session.add(ws)
        session.flush()
        session.commit()
        session.refresh(ws)
        return ws

    except ValueError:
        raise
    except RuntimeError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected create_slack_workspace: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def get_slack_workspace_by_id(slack_workspace_id: int,*,session: optional[SASession] = None) -> optional[model.SlackWorkspace]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        return session.get(model.SlackWorkspace, int(slack_workspace_id))
    finally:
        if own_session:
            session.close()

def get_slack_workspace_by_team_id(team_id: str,*,session: optional[SASession] = None) -> optional[model.SlackWorkspace]:
    team_id = (team_id or "").strip()
    if not team_id:
        return None

    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        return session.execute(stmt).scalar_one_or_none()
    finally:
        if own_session:
            session.close()

def list_slack_workspaces_for_company(company_id: int,*,include_revoked: bool = True,session: optional[SASession] = None) -> list[model.SlackWorkspace]:
    own_session = session is None
    if own_session:
        session = Session()
    try:
        stmt = select(model.SlackWorkspace).where(model.SlackWorkspace.company_id == int(company_id))
        if not include_revoked:
            stmt = stmt.where(model.SlackWorkspace.revoked_at.is_(None))
        stmt = stmt.order_by(model.SlackWorkspace.installed_at.asc(), model.SlackWorkspace.team_id.asc())
        return session.execute(stmt).scalars().all()
    finally:
        if own_session:
            session.close()

def update_slack_workspace_access_token(team_id: str,*,access_token: str,session: optional[SASession] = None) -> optional[model.SlackWorkspace]:
    """
    Update the access token for an installed workspace.
    Returns updated workspace or None if not found.
    """
    team_id = (team_id or "").strip()
    access_token = (access_token or "").strip()
    if not team_id:
        raise ValueError("team_id is required.")
    if not access_token:
        raise ValueError("access_token is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        ws = session.execute(
            select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        ).scalar_one_or_none()
        if not ws:
            return None

        ws.access_token = access_token
        session.commit()
        session.refresh(ws)
        return ws

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected update_slack_workspace_access_token: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def revoke_slack_workspace(team_id: str,*,session: optional[SASession] = None) -> bool:
    """
    Marks a workspace as revoked (revoked_at=now()).
    Returns True if revoked, False if not found or already revoked.
    """
    team_id = (team_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        ws = session.execute(
            select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        ).scalar_one_or_none()
        if not ws:
            return False
        if ws.revoked_at is not None:
            return False

        ws.revoked_at = datetime.now(timezone.utc)
        session.commit()
        return True

    except ValueError:
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def reinstall_slack_workspace(team_id: str,*,access_token: str,session: optional[SASession] = None) -> optional[model.SlackWorkspace]:
    """
    If a workspace exists (revoked or not), update token and clear revoked_at.
    Returns updated workspace or None if not found.
    """
    team_id = (team_id or "").strip()
    access_token = (access_token or "").strip()
    if not team_id:
        raise ValueError("team_id is required.")
    if not access_token:
        raise ValueError("access_token is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        ws = session.execute(
            select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        ).scalar_one_or_none()
        if not ws:
            return None

        ws.access_token = access_token
        ws.revoked_at = None
        session.commit()
        session.refresh(ws)
        return ws

    except ValueError:
        raise
    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"DB rejected reinstall_slack_workspace: {e.orig}") from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def hard_delete_slack_workspace(team_id: str,*,session: optional[SASession] = None) -> bool:
    """
    Hard delete a slack workspace by team_id.
    WARNING: Will fail if slack_accounts reference it (FK RESTRICT via composite FK).
    """
    team_id = (team_id or "").strip()
    if not team_id:
        raise ValueError("team_id is required.")

    own_session = session is None
    if own_session:
        session = Session()

    try:
        ws = session.execute(
            select(model.SlackWorkspace).where(model.SlackWorkspace.team_id == team_id)
        ).scalar_one_or_none()
        if not ws:
            return False

        session.delete(ws)
        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        raise RuntimeError(
            f"DB rejected hard_delete_slack_workspace (workspace likely referenced): {e.orig}"
        ) from e
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()
