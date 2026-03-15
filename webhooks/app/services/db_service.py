import uuid
from datetime import datetime
from typing import Optional
 
from backend.New_database import new_crud as crud
from backend.New_database import new_crud_second_half as crud2
from backend.New_database import new_oop as model
 
 
# ── Canonical viewer seats ────────────────────────────────────────
 
def create_viewer_seat(
    company_id: int,
    display_name: str,
    *,
    session=None,
) -> model.User:
    return crud.create_user(
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
    return crud.get_user_by_id(company_id, user_id, session=session)
 
 
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
    return crud2.create_google_mailbox(
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
    return crud2.get_google_mailbox_by_email(
        company_id, email_address, session=session
    )
 
 
def update_google_mailbox_token(
    google_mailbox_id: int,
    token_json: dict,
    *,
    session=None,
) -> Optional[model.GoogleMailbox]:
    return crud2.update_google_mailbox_token(
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
    crud2.set_google_mailbox_history_id(
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
    crud2.update_google_mailbox_watch_expiration(
        google_mailbox_id,
        watch_expiration=watch_expiration,
        session=session,
    )
 
 
def list_google_mailboxes_for_company(
    company_id: int,
    *,
    session=None,
) -> list[model.GoogleMailbox]:
    return crud2.list_google_mailboxes_for_company(company_id, session=session)
 
 
# ── Slack Workspaces ──────────────────────────────────────────────
 
def create_workspace(
    company_id: int,
    team_id: str,
    access_token: str,
    *,
    session=None,
) -> model.SlackWorkspace:
    return crud2.create_workspace(
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
    return crud2.get_workspace_by_team_id(team_id, session=session)
 
 
def update_workspace_token(
    team_id: str,
    access_token: str,
    *,
    session=None,
) -> Optional[model.SlackWorkspace]:
    return crud2.update_workspace_token(team_id, access_token, session=session)
 
 
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
    return crud2.create_slack_account(
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
    return crud2.get_slack_account(team_id, slack_user_id, session=session)
 
 
def update_slack_account_email(
    team_id: str,
    slack_user_id: str,
    email: Optional[str],
    *,
    session=None,
) -> None:
    """Update the email metadata on a slack_accounts row."""
    crud2.update_slack_account_email(
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
    return crud2.create_message_incident(
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
    crud2.create_incident_scores(
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