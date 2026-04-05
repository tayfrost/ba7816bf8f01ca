"""
Integration tests for db_service.py

Real HTTP calls to the internal API (no mocks). API + pgvector must be running.
Fixture creates test company via API before each test, cleans up after.

Run with:
    pytest tests/test_db_service.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.services import db_service as db


# ── Helpers ───────────────────────────────────────────────────────

def _utcnow():
    return datetime.now(tz=timezone.utc)


# ── Viewer seats ──────────────────────────────────────────────────

class TestCreateViewerSeat:

    def test_creates_viewer_with_display_name(self, test_company_id):
        result = db.create_viewer_seat(test_company_id, display_name="Alice")
        assert result is not None
        assert result.company_id == test_company_id
        assert result.role == "viewer"
        assert result.status == "active"
        assert result.display_name == "Alice"
        assert uuid.UUID(str(result.user_id))  # valid UUID (may be str from API)

    def test_creates_viewer_without_display_name(self, test_company_id):
        result = db.create_viewer_seat(test_company_id, display_name=None)
        assert result is not None
        assert result.company_id == test_company_id
        assert result.role == "viewer"
        assert result.status == "active"


# ── User retrieval ────────────────────────────────────────────────

class TestGetUserById:

    def test_returns_user_when_found(self, test_company_id):
        # Create a user first
        created = db.create_viewer_seat(test_company_id, display_name="Bob")

        # Retrieve it
        retrieved = db.get_user_by_id(test_company_id, created.user_id)
        assert retrieved is not None
        assert retrieved.user_id == created.user_id
        assert retrieved.company_id == test_company_id
        assert retrieved.display_name == "Bob"

    def test_returns_none_when_not_found(self, test_company_id):
        fake_id = uuid.uuid4()
        result = db.get_user_by_id(test_company_id, fake_id)
        assert result is None


# ── Google mailboxes ──────────────────────────────────────────────

class TestCreateGoogleMailbox:

    def test_creates_mailbox_with_all_fields(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Mailbox Owner")

        result = db.create_google_mailbox(
            test_company_id,
            user.user_id,
            "emp@example.com",
            {"token": "abc", "refresh_token": "xyz"}
        )

        assert result is not None
        assert result.company_id == test_company_id
        assert result.user_id == user.user_id
        assert result.email_address == "emp@example.com"
        assert result.token_json == {"token": "abc", "refresh_token": "xyz"}
        assert result.google_mailbox_id is not None


# ── Mailbox retrieval ─────────────────────────────────────────────

class TestGetGoogleMailboxByEmail:

    def test_returns_mailbox_when_found(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        created = db.create_google_mailbox(
            test_company_id,
            user.user_id,
            "test@example.com",
            {"token": "t"}
        )

        retrieved = db.get_google_mailbox_by_email(test_company_id, "test@example.com")
        assert retrieved is not None
        assert retrieved.email_address == "test@example.com"
        assert retrieved.google_mailbox_id == created.google_mailbox_id

    def test_returns_none_when_not_found(self, test_company_id):
        result = db.get_google_mailbox_by_email(test_company_id, "nonexistent@example.com")
        assert result is None


# ── Mailbox token updates ─────────────────────────────────────────

class TestUpdateGoogleMailboxToken:

    def test_updates_token_successfully(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        mailbox = db.create_google_mailbox(
            test_company_id,
            user.user_id,
            "mail@example.com",
            {"token": "old"}
        )

        new_token = {"token": "new_token", "refresh": "new_refresh"}
        result = db.update_google_mailbox_token(mailbox.google_mailbox_id, new_token)

        assert result is not None
        assert result.token_json == new_token


# ── Mailbox history ID ────────────────────────────────────────────

class TestSetGoogleMailboxHistoryId:

    def test_sets_history_id(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        mailbox = db.create_google_mailbox(
            test_company_id,
            user.user_id,
            "mail@example.com",
            {"token": "t"}
        )

        # Should not raise
        db.set_google_mailbox_history_id(mailbox.google_mailbox_id, "99999")

        # Verify by retrieving
        retrieved = db.get_google_mailbox_by_email(test_company_id, "mail@example.com")
        assert retrieved.last_history_id == "99999"


# ── Mailbox watch expiration ──────────────────────────────────────

class TestUpdateGoogleMailboxWatchExpiration:

    def test_sets_watch_expiration(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        mailbox = db.create_google_mailbox(
            test_company_id,
            user.user_id,
            "mail@example.com",
            {"token": "t"}
        )

        expiry = _utcnow()
        # Should not raise
        db.update_google_mailbox_watch_expiration(mailbox.google_mailbox_id, expiry)

        # Verify by retrieving
        retrieved = db.get_google_mailbox_by_email(test_company_id, "mail@example.com")
        # Note: watch_expiration may be slightly different due to serialization
        assert retrieved.watch_expiration is not None


# ── List mailboxes ────────────────────────────────────────────────

class TestListGoogleMailboxesForCompany:

    def test_returns_all_mailboxes_for_company(self, test_company_id):
        user1 = db.create_viewer_seat(test_company_id, display_name="User1")
        user2 = db.create_viewer_seat(test_company_id, display_name="User2")

        mb1 = db.create_google_mailbox(test_company_id, user1.user_id, "mb1@example.com", {})
        mb2 = db.create_google_mailbox(test_company_id, user2.user_id, "mb2@example.com", {})

        result = db.list_google_mailboxes_for_company(test_company_id)

        # Should contain at least our two
        assert len(result) >= 2
        emails = [m.email_address for m in result]
        assert "mb1@example.com" in emails
        assert "mb2@example.com" in emails


# ── Slack workspaces ──────────────────────────────────────────────

class TestCreateWorkspace:

    def test_creates_workspace(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        result = db.create_workspace(
            test_company_id,
            team_id,
            "xoxb-123-slack-token"
        )

        assert result is not None
        assert result.company_id == test_company_id
        assert result.team_id == team_id
        assert result.access_token == "xoxb-123-slack-token"


# ── Workspace retrieval ───────────────────────────────────────────

class TestGetWorkspaceByTeamId:

    def test_returns_workspace_when_found(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        created = db.create_workspace(test_company_id, team_id, "xoxb-token")

        retrieved = db.get_workspace_by_team_id(team_id)
        assert retrieved is not None
        assert retrieved.team_id == team_id
        assert retrieved.company_id == test_company_id

    def test_returns_none_when_not_found(self):
        result = db.get_workspace_by_team_id("T_NONEXISTENT_12345")
        assert result is None


# ── Workspace token updates ───────────────────────────────────────

class TestUpdateWorkspaceToken:

    def test_updates_token(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        created = db.create_workspace(test_company_id, team_id, "xoxb-old")

        result = db.update_workspace_token(team_id, "xoxb-new-token")

        assert result is not None
        assert result.access_token == "xoxb-new-token"


# ── Slack accounts ────────────────────────────────────────────────

class TestCreateSlackAccount:

    def test_creates_slack_account(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        db.create_workspace(test_company_id, team_id, "xoxb-token")
        user = db.create_viewer_seat(test_company_id, display_name="Slack User")

        result = db.create_slack_account(
            test_company_id,
            team_id,
            "U999",
            user.user_id,
            email="slack@example.com"
        )

        assert result is not None
        assert result.company_id == test_company_id
        assert result.team_id == team_id
        assert result.slack_user_id == "U999"
        assert result.user_id == user.user_id
        assert result.email == "slack@example.com"


# ── Slack account retrieval ───────────────────────────────────────

class TestGetSlackAccount:

    def test_returns_account_when_found(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        db.create_workspace(test_company_id, team_id, "xoxb-token")
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        created = db.create_slack_account(
            test_company_id,
            team_id,
            "U222",
            user.user_id
        )

        retrieved = db.get_slack_account(team_id, "U222")
        assert retrieved is not None
        assert retrieved.slack_user_id == "U222"
        assert retrieved.team_id == team_id

    def test_returns_none_when_not_found(self):
        result = db.get_slack_account("T_FAKE", "U_NONEXISTENT")
        assert result is None


# ── Slack account email updates ───────────────────────────────────

class TestUpdateSlackAccountEmail:

    def test_updates_email(self, test_company_id):
        team_id = f"T{uuid.uuid4().hex[:8].upper()}"
        db.create_workspace(test_company_id, team_id, "xoxb-token")
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        acct = db.create_slack_account(
            test_company_id,
            team_id,
            "U666",
            user.user_id,
            email="old@example.com"
        )

        # Should not raise
        db.update_slack_account_email(team_id, "U666", "new@example.com")

        # Verify
        retrieved = db.get_slack_account(team_id, "U666")
        assert retrieved.email == "new@example.com"


# ── Message incidents ─────────────────────────────────────────────

class TestCreateMessageIncident:

    def test_creates_incident_with_slack_source(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        sent = _utcnow()

        result = db.create_message_incident(
            test_company_id,
            user.user_id,
            "slack",
            sent,
            {"text": "hello"},
            conversation_id="C123"
        )

        assert result is not None
        assert result.company_id == test_company_id
        assert result.user_id == user.user_id
        assert result.source == "slack"
        assert result.content_raw == {"text": "hello"}
        assert result.conversation_id == "C123"

    def test_creates_incident_with_gmail_source(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        sent = _utcnow()

        result = db.create_message_incident(
            test_company_id,
            user.user_id,
            "gmail",
            sent,
            {"subject": "test"},
            conversation_id="msg123"
        )

        assert result is not None
        assert result.source == "gmail"
        assert result.conversation_id == "msg123"


# ── Incident scores ───────────────────────────────────────────────

class TestCreateIncidentScores:

    def test_creates_scores(self, test_company_id):
        user = db.create_viewer_seat(test_company_id, display_name="Test")
        incident = db.create_message_incident(
            test_company_id,
            user.user_id,
            "slack",
            _utcnow(),
            {},
        )

        # Should not raise
        db.create_incident_scores(
            incident.message_id,
            predicted_category="stress",
            predicted_severity=1,
        )

        # Verify (would need a get_incident_scores function to fully verify)
        # For now, just ensure no error on creation
        assert incident.message_id is not None
