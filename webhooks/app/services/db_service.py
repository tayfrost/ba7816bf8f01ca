import uuid
from datetime import datetime
from typing import Optional
 
import database.New_database.utils.users_crud as users_crud
import database.New_database.utils.crud_google_mailboxes as crud_google_mailboxes
import database.New_database.utils.companies_crud as companies_crud
import database.New_database.utils.slack_workspaces_crud as slack_workspaces_crud
import database.New_database.utils.crud_slack_accounts as crud_slack_accounts
import database.New_database.utils.crud_message_incidents as crud_message_incidents
from database.New_database import new_oop as model
 
 
# ── Canonical viewer seats ────────────────────────────────────────
 
def create_viewer_seat(
    company_id: int,
    display_name: str,
    *,
    session=None,
) -> model.User:
    return users_crud.create_user(
        company_id,
        role="viewer",
        status="active",
        display_name=display_name,
        session=session,
    )
 
 
def get_user_by_id(
    company_id: int,
    user_id: uuid.UUID,
    *,
    session=None,
) -> Optional[model.User]:
    """Fetch a users row by (company_id, user_id). Returns None if not found."""
    return users_crud.get_user_by_id(company_id, user_id, session=session)
 
 
# ── Google Mailboxes ──────────────────────────────────────────────
 
def create_google_mailbox(
    company_id: int,
    user_id: uuid.UUID,
    email_address: str,
    token_json: dict,
    *,
    session=None,
) -> model.GoogleMailbox:
    """
    Create a google_mailboxes row.
    Raises RuntimeError if the mailbox already exists (from crud).
    Call get_google_mailbox_by_email first if you need upsert behaviour.
    """
    return crud_google_mailboxes.create_google_mailbox(
        company_id,
        user_id=user_id,
        email_address=email_address,
        token_json=token_json,
        session=session,
    )
 
 
def get_google_mailbox_by_email(
    company_id: int,
    email_address: str,
    *,
    session=None,
) -> Optional[model.GoogleMailbox]:
    """Fetch a google_mailboxes row by (company_id, email_address)."""
    return crud_google_mailboxes.get_google_mailbox_by_email(
        company_id, email_address, session=session
    )
 
 
def update_google_mailbox_token(
    google_mailbox_id: int,
    token_json: dict,
    *,
    session=None,
) -> Optional[model.GoogleMailbox]:
    return crud_google_mailboxes.update_google_mailbox_token(
        google_mailbox_id,
        token_json=token_json,
        session=session,
    )
 
 
def set_google_mailbox_history_id(
    google_mailbox_id: int,
    last_history_id: str,
    *,
    session=None,
) -> None:
    crud_google_mailboxes.set_google_mailbox_history_id(
        google_mailbox_id,
        last_history_id=last_history_id,
        session=session,
    )
 
 
def update_google_mailbox_watch_expiration(
    google_mailbox_id: int,
    watch_expiration: datetime,
    *,
    session=None,
) -> None:
    crud_google_mailboxes.update_google_mailbox_watch_expiration(
        google_mailbox_id,
        watch_expiration=watch_expiration,
        session=session,
    )
 
 
def list_google_mailboxes_for_company(
    company_id: int,
    *,
    session=None,
) -> list[model.GoogleMailbox]:
    return crud_google_mailboxes.list_google_mailboxes_for_company(company_id, session=session)

# ── Companies ──────────────────────────────────────────────
def list_companies(
    *,
    session=None,
) -> list[model.Company]:
    """Return all active (non-deleted) companies. Used by the watch renewal job."""
    return companies_crud.list_companies(session=session)


# ── Slack Workspaces ──────────────────────────────────────────────
 
def create_workspace(
    company_id: int,
    team_id: str,
    access_token: str,
    *,
    session=None,
) -> model.SlackWorkspace:
    return slack_workspaces_crud.create_workspace(
        company_id=company_id,
        team_id=team_id,
        access_token=access_token,
        session=session,
    )
 
 
def get_workspace_by_team_id(
    team_id: str,
    *,
    session=None,
) -> Optional[model.SlackWorkspace]:
    return slack_workspaces_crud.get_workspace_by_team_id(team_id, session=session)
 
 
def update_workspace_token(
    team_id: str,
    access_token: str,
    *,
    session=None,
) -> Optional[model.SlackWorkspace]:
    return slack_workspaces_crud.update_workspace_token(team_id, access_token, session=session)
 
 
# ── Slack Accounts ────────────────────────────────────────────────
 
def create_slack_account(
    company_id: int,
    team_id: str,
    slack_user_id: str,
    user_id: uuid.UUID,
    email: Optional[str] = None,
    *,
    session=None,
) -> model.SlackAccount:
    """
    Create a slack_accounts row.
    Raises RuntimeError if the account already exists (from crud).
    Call get_slack_account first if you need upsert behaviour.
    """
    return crud_slack_accounts.create_slack_account(
        company_id,
        team_id=team_id,
        slack_user_id=slack_user_id,
        user_id=user_id,
        email=email,
        session=session,
    )
 
 
def get_slack_account(
    team_id: str,
    slack_user_id: str,
    *,
    session=None,
) -> Optional[model.SlackAccount]:
    """Fetch a slack_accounts row by (team_id, slack_user_id)."""
    return crud_slack_accounts.get_slack_account(team_id, slack_user_id, session=session)
 
 
def update_slack_account_email(
    team_id: str,
    slack_user_id: str,
    email: Optional[str],
    *,
    session=None,
) -> None:
    """Update the email metadata on a slack_accounts row."""
    crud_slack_accounts.update_slack_account_email(
        team_id, slack_user_id,
        email=email,
        session=session,
    )
 
 
# ── Message Incidents ─────────────────────────────────────────────
 
def create_message_incident(
    company_id: int,
    user_id: uuid.UUID,
    source: str,
    sent_at: datetime,
    content_raw: dict,
    conversation_id: Optional[str] = None,
    *,
    session=None,
) -> model.MessageIncident:
    """Create a message_incidents row. Returns the created incident."""
    return crud_message_incidents.create_message_incident(
        company_id,
        user_id=user_id,
        source=source,
        sent_at=sent_at,
        content_raw=content_raw,
        conversation_id=conversation_id,
        session=session,
    )
 
 
def create_incident_scores(
    message_id: uuid.UUID,
    *,
    neutral_score: float = 0.0,
    humor_sarcasm_score: float = 0.0,
    stress_score: float = 0.0,
    burnout_score: float = 0.0,
    depression_score: float = 0.0,
    harassment_score: float = 0.0,
    suicidal_ideation_score: float = 0.0,
    predicted_category: Optional[str] = None,
    predicted_severity: Optional[int] = None,
    session=None,
) -> None:
    """Create an incident_scores row (1:1 with message_incidents)."""
    crud_message_incidents.create_incident_scores(
        message_id,
        neutral_score=neutral_score,
        humor_sarcasm_score=humor_sarcasm_score,
        stress_score=stress_score,
        burnout_score=burnout_score,
        depression_score=depression_score,
        harassment_score=harassment_score,
        suicidal_ideation_score=suicidal_ideation_score,
        predicted_category=predicted_category,
        predicted_severity=predicted_severity,
        session=session,
    )
