# app/services/db_stub.py
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Gmail ────────────────────────────────────────────────────────

def create_gmail_account(company_id: int, user_email: str, token_json: str):
    logger.info(f"[STUB] create_gmail_account: {user_email} company={company_id}")
    return {"user_email": user_email, "company_id": company_id}

def get_gmail_account_by_email(user_email: str):
    logger.info(f"[STUB] get_gmail_account_by_email: {user_email}")
    # Returning a fake account so the webhook pipeline runs end to end
    class FakeAccount:
        company_id = 1
        last_history_id = None
        watch_expiration = None
        token_json = None
    return FakeAccount()

def update_gmail_history_id(user_email: str, last_history_id: str):
    logger.info(f"[STUB] update_gmail_history_id: {user_email} -> {last_history_id}")

def update_gmail_watch(user_email: str, last_history_id: str, watch_expiration: datetime):
    logger.info(f"[STUB] update_gmail_watch: {user_email} expires={watch_expiration}")

def list_gmail_accounts():
    logger.info("[STUB] list_gmail_accounts")
    return []

# ── Slack ────────────────────────────────────────────────────────

def upsert_workspace_by_team_id(company_id: int, team_id: str, access_token: str):
    logger.info(f"[STUB] upsert_workspace: team={team_id} company={company_id}")
    return {"team_id": team_id, "company_id": company_id}

def get_workspace_by_team_id(team_id: str):
    logger.info(f"[STUB] get_workspace_by_team_id: {team_id}")
    class FakeWorkspace:
        company_id = 1
        access_token = "xoxb-stub-token"
    return FakeWorkspace()

def upsert_slack_user(team_id: str, slack_user_id: str, name: str, surname: str):
    logger.info(f"[STUB] upsert_slack_user: {slack_user_id} team={team_id}")

def create_flagged_incident(*, company_id, team_id, slack_user_id,
                             message_ts, channel_id, raw_message_text, class_reason=None):
    logger.info(
        f"[STUB] create_flagged_incident: company={company_id} "
        f"team={team_id} user={slack_user_id} channel={channel_id}"
    )
    logger.info(f"[STUB] raw_message_text: {raw_message_text}")