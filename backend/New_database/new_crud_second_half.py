"""
Re-export hub for backward compatibility.

The CRUD functions are now organized in domain-specific modules:
  - crud_slack_accounts
  - crud_google_mailboxes
  - crud_auth_users
  - crud_message_incidents
  - crud_incident_scores
"""

from backend.New_database.crud_slack_accounts import (
    create_slack_account,
    get_slack_account,
    list_slack_accounts_for_company,
    list_slack_accounts_for_user,
    update_slack_account_email,
    hard_delete_slack_account,
)
from backend.New_database.crud_google_mailboxes import (
    _increment_history_id,
    create_google_mailbox,
    get_google_mailbox_by_id,
    list_google_mailboxes_for_company,
    list_google_mailboxes_for_user,
    get_google_mailbox_by_email,
    update_google_mailbox_token,
    increment_google_mailbox_history_id,
    set_google_mailbox_history_id,
    update_google_mailbox_watch_expiration,
    hard_delete_google_mailbox,
)
from backend.New_database.crud_auth_users import (
    create_auth_user,
    get_auth_user_by_id,
    get_auth_user_by_email,
    get_auth_user_by_user_id,
    list_auth_users_for_company,
    update_auth_user_password,
    update_auth_user_email,
    update_auth_user_link,
    hard_delete_auth_user,
)
from backend.New_database.crud_message_incidents import (
    VALID_SOURCES,
    create_message_incident,
    get_message_incident_by_id,
    list_message_incidents_for_company,
    list_message_incidents_for_user,
    hard_delete_message_incident,
)
from backend.New_database.crud_incident_scores import (
    create_incident_scores,
    get_incident_scores_by_message_id,
    get_incident_scores_by_id,
    update_incident_scores,
    hard_delete_incident_scores,
)
