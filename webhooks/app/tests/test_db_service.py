"""
Isolated unit tests for db_service.py

Verifies that every function delegates correctly to the right crud / crud2
function with the right arguments. No real DB, sessions, or network calls.

Run with:
    pytest tests/test_db_service.py -v
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


# ── Helpers ───────────────────────────────────────────────────────

def _utcnow():
    return datetime.now(tz=timezone.utc)


def _make_user(**kw):
    return SimpleNamespace(
        user_id=uuid.uuid4(), company_id=1, role="viewer",
        status="active", display_name="Test User", deleted_at=None, **kw
    )


def _make_mailbox(**kw):
    return SimpleNamespace(
        google_mailbox_id=10, company_id=1, user_id=uuid.uuid4(),
        email_address="emp@example.com", token_json={"token": "t"},
        last_history_id=None, watch_expiration=None, **kw
    )


def _make_workspace(**kw):
    return SimpleNamespace(
        slack_workspace_id=1, company_id=1, team_id="T123",
        access_token="xoxb-token", revoked_at=None, **kw
    )


def _make_slack_account(**kw):
    return SimpleNamespace(
        company_id=1, team_id="T123", slack_user_id="U999",
        user_id=uuid.uuid4(), email=None, **kw
    )


def _make_incident(**kw):
    return SimpleNamespace(
        message_id=uuid.uuid4(), company_id=1, user_id=uuid.uuid4(),
        source="slack", sent_at=_utcnow(), content_raw={},
        conversation_id=None, **kw
    )


# ── Viewer seats ──────────────────────────────────────────────────

class TestCreateViewerSeat:

    def test_calls_create_user_with_viewer_role(self, monkeypatch):
        new_user = _make_user()
        captured = {}

        def fake(company_id, role, status, display_name, session=None):
            captured.update(company_id=company_id, role=role,
                            status=status, display_name=display_name)
            return new_user

        monkeypatch.setattr("app.services.db_service.crud.create_user", fake)
        from app.services import db_service as db
        result = db.create_viewer_seat(1, display_name="Alice")
        assert result is new_user
        assert captured["role"]         == "viewer"
        assert captured["status"]       == "active"
        assert captured["display_name"] == "Alice"
        assert captured["company_id"]   == 1

    def test_passes_company_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.services.db_service.crud.create_user",
            lambda cid, role, status, display_name, session=None: (
                captured.update(company_id=cid) or _make_user()
            ),
        )
        from app.services import db_service as db
        db.create_viewer_seat(42, display_name="Bob")
        assert captured["company_id"] == 42


class TestGetUserById:

    def test_returns_user_when_found(self, monkeypatch):
        user = _make_user()
        monkeypatch.setattr(
            "app.services.db_service.crud.get_user_by_id",
            lambda cid, uid, session=None: user,
        )
        from app.services import db_service as db
        assert db.get_user_by_id(1, user.user_id) is user

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.db_service.crud.get_user_by_id",
            lambda cid, uid, session=None: None,
        )
        from app.services import db_service as db
        assert db.get_user_by_id(1, uuid.uuid4()) is None


# ── Google mailboxes ──────────────────────────────────────────────

class TestCreateGoogleMailbox:

    def test_delegates_all_fields(self, monkeypatch):
        mailbox  = _make_mailbox()
        captured = {}

        def fake(cid, *, user_id, email_address, token_json, session=None):
            captured.update(company_id=cid, user_id=user_id,
                            email_address=email_address, token_json=token_json)
            return mailbox

        monkeypatch.setattr("app.services.db_service.crud2.create_google_mailbox", fake)
        from app.services import db_service as db
        uid    = uuid.uuid4()
        result = db.create_google_mailbox(1, uid, "emp@example.com", {"t": "v"})
        assert result is mailbox
        assert captured["user_id"]       == uid
        assert captured["email_address"] == "emp@example.com"
        assert captured["token_json"]    == {"t": "v"}


class TestGetGoogleMailboxByEmail:

    def test_returns_mailbox_when_found(self, monkeypatch):
        mailbox = _make_mailbox()
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_google_mailbox_by_email",
            lambda cid, email, session=None: mailbox,
        )
        from app.services import db_service as db
        assert db.get_google_mailbox_by_email(1, "emp@example.com") is mailbox

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_google_mailbox_by_email",
            lambda cid, email, session=None: None,
        )
        from app.services import db_service as db
        assert db.get_google_mailbox_by_email(1, "unknown@example.com") is None


class TestUpdateGoogleMailboxToken:

    def test_passes_mailbox_id_and_token(self, monkeypatch):
        captured = {}

        def fake(mid, *, token_json, session=None):
            captured.update(mailbox_id=mid, token_json=token_json)
            return _make_mailbox()

        monkeypatch.setattr(
            "app.services.db_service.crud2.update_google_mailbox_token", fake
        )
        from app.services import db_service as db
        db.update_google_mailbox_token(10, {"new": "token"})
        assert captured["mailbox_id"] == 10
        assert captured["token_json"] == {"new": "token"}


class TestSetGoogleMailboxHistoryId:

    def test_passes_mailbox_id_and_history_id(self, monkeypatch):
        captured = {}

        def fake(mid, *, last_history_id, session=None):
            captured.update(mailbox_id=mid, last_history_id=last_history_id)

        monkeypatch.setattr(
            "app.services.db_service.crud2.set_google_mailbox_history_id", fake
        )
        from app.services import db_service as db
        db.set_google_mailbox_history_id(10, "99999")
        assert captured["mailbox_id"]      == 10
        assert captured["last_history_id"] == "99999"


class TestUpdateGoogleMailboxWatchExpiration:

    def test_passes_mailbox_id_and_expiry(self, monkeypatch):
        expiry   = _utcnow()
        captured = {}

        def fake(mid, *, watch_expiration, session=None):
            captured.update(mailbox_id=mid, watch_expiration=watch_expiration)

        monkeypatch.setattr(
            "app.services.db_service.crud2.update_google_mailbox_watch_expiration", fake
        )
        from app.services import db_service as db
        db.update_google_mailbox_watch_expiration(10, expiry)
        assert captured["mailbox_id"]       == 10
        assert captured["watch_expiration"] == expiry


class TestListGoogleMailboxesForCompany:

    def test_returns_list_from_crud(self, monkeypatch):
        mailboxes = [_make_mailbox(), _make_mailbox(google_mailbox_id=11)]
        monkeypatch.setattr(
            "app.services.db_service.crud2.list_google_mailboxes_for_company",
            lambda cid, session=None: mailboxes,
        )
        from app.services import db_service as db
        result = db.list_google_mailboxes_for_company(1)
        assert result == mailboxes
        assert len(result) == 2


# ── Slack workspaces ──────────────────────────────────────────────

class TestCreateWorkspace:

    def test_delegates_company_team_token(self, monkeypatch):
        ws       = _make_workspace()
        captured = {}

        def fake(*, company_id, team_id, access_token, session=None):
            captured.update(company_id=company_id, team_id=team_id,
                            access_token=access_token)
            return ws

        monkeypatch.setattr("app.services.db_service.crud2.create_workspace", fake)
        from app.services import db_service as db
        result = db.create_workspace(1, "T123", "xoxb-token")
        assert result is ws
        assert captured["company_id"]   == 1
        assert captured["team_id"]      == "T123"
        assert captured["access_token"] == "xoxb-token"


class TestGetWorkspaceByTeamId:

    def test_returns_workspace_when_found(self, monkeypatch):
        ws = _make_workspace()
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_workspace_by_team_id",
            lambda tid, session=None: ws,
        )
        from app.services import db_service as db
        assert db.get_workspace_by_team_id("T123") is ws

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_workspace_by_team_id",
            lambda tid, session=None: None,
        )
        from app.services import db_service as db
        assert db.get_workspace_by_team_id("T_UNKNOWN") is None


class TestUpdateWorkspaceToken:

    def test_passes_team_id_and_token(self, monkeypatch):
        captured = {}

        def fake(team_id, access_token, session=None):
            captured.update(team_id=team_id, access_token=access_token)
            return _make_workspace()

        monkeypatch.setattr(
            "app.services.db_service.crud2.update_workspace_token", fake
        )
        from app.services import db_service as db
        db.update_workspace_token("T123", "xoxb-new")
        assert captured["team_id"]      == "T123"
        assert captured["access_token"] == "xoxb-new"


# ── Slack accounts ────────────────────────────────────────────────

class TestCreateSlackAccount:

    def test_delegates_all_fields(self, monkeypatch):
        acct     = _make_slack_account()
        captured = {}

        def fake(cid, *, team_id, slack_user_id, user_id, email, session=None):
            captured.update(company_id=cid, team_id=team_id,
                            slack_user_id=slack_user_id, user_id=user_id)
            return acct

        monkeypatch.setattr(
            "app.services.db_service.crud2.create_slack_account", fake
        )
        from app.services import db_service as db
        uid    = uuid.uuid4()
        result = db.create_slack_account(1, "T123", "U999", uid)
        assert result is acct
        assert captured["slack_user_id"] == "U999"
        assert captured["user_id"]       == uid


class TestGetSlackAccount:

    def test_returns_account_when_found(self, monkeypatch):
        acct = _make_slack_account()
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_slack_account",
            lambda tid, uid, session=None: acct,
        )
        from app.services import db_service as db
        assert db.get_slack_account("T123", "U999") is acct

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.db_service.crud2.get_slack_account",
            lambda tid, uid, session=None: None,
        )
        from app.services import db_service as db
        assert db.get_slack_account("T123", "U_UNKNOWN") is None


class TestUpdateSlackAccountEmail:

    def test_passes_team_user_and_email(self, monkeypatch):
        captured = {}

        def fake(team_id, slack_user_id, *, email, session=None):
            captured.update(team_id=team_id, slack_user_id=slack_user_id,
                            email=email)

        monkeypatch.setattr(
            "app.services.db_service.crud2.update_slack_account_email", fake
        )
        from app.services import db_service as db
        db.update_slack_account_email("T123", "U999", "real@example.com")
        assert captured["team_id"]       == "T123"
        assert captured["slack_user_id"] == "U999"
        assert captured["email"]         == "real@example.com"


# ── Message incidents ─────────────────────────────────────────────

class TestCreateMessageIncident:

    def test_delegates_all_fields(self, monkeypatch):
        incident = _make_incident()
        captured = {}
        sent     = _utcnow()

        def fake(cid, *, user_id, source, sent_at, content_raw,
                 conversation_id, session=None):
            captured.update(company_id=cid, source=source,
                            sent_at=sent_at, conversation_id=conversation_id)
            return incident

        monkeypatch.setattr(
            "app.services.db_service.crud2.create_message_incident", fake
        )
        from app.services import db_service as db
        uid    = uuid.uuid4()
        result = db.create_message_incident(
            1, uid, "slack", sent, {"text": "hi"}, conversation_id="C1"
        )
        assert result is incident
        assert captured["source"]          == "slack"
        assert captured["conversation_id"] == "C1"
        assert captured["sent_at"]         == sent

    def test_slack_source_label(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.services.db_service.crud2.create_message_incident",
            lambda cid, *, user_id, source, sent_at, content_raw,
                   conversation_id, session=None: (
                captured.update(source=source) or _make_incident()
            ),
        )
        from app.services import db_service as db
        db.create_message_incident(
            1, uuid.uuid4(), "slack", _utcnow(), {}, conversation_id=None
        )
        assert captured["source"] == "slack"

    def test_gmail_source_label(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.services.db_service.crud2.create_message_incident",
            lambda cid, *, user_id, source, sent_at, content_raw,
                   conversation_id, session=None: (
                captured.update(source=source) or _make_incident()
            ),
        )
        from app.services import db_service as db
        db.create_message_incident(
            1, uuid.uuid4(), "gmail", _utcnow(), {}, conversation_id="gmail"
        )
        assert captured["source"] == "gmail"


class TestCreateIncidentScores:

    def test_delegates_message_id_and_scores(self, monkeypatch):
        captured = {}

        def fake(mid, *, neutral_score, humor_sarcasm_score, stress_score,
                 burnout_score, depression_score, harassment_score,
                 suicidal_ideation_score, predicted_category,
                 predicted_severity, session=None):
            captured.update(
                message_id=mid, stress_score=stress_score,
                predicted_category=predicted_category,
                predicted_severity=predicted_severity,
            )

        monkeypatch.setattr(
            "app.services.db_service.crud2.create_incident_scores", fake
        )
        from app.services import db_service as db
        mid = uuid.uuid4()
        db.create_incident_scores(
            mid, stress_score=0.9,
            predicted_category="stress", predicted_severity=1,
        )
        assert captured["message_id"]         == mid
        assert captured["stress_score"]       == 0.9
        assert captured["predicted_category"] == "stress"
        assert captured["predicted_severity"] == 1

    def test_score_defaults_are_zero(self, monkeypatch):
        captured = {}

        def fake(mid, *, neutral_score, humor_sarcasm_score, stress_score,
                 burnout_score, depression_score, harassment_score,
                 suicidal_ideation_score, predicted_category,
                 predicted_severity, session=None):
            captured.update(
                neutral_score=neutral_score,
                burnout_score=burnout_score,
                harassment_score=harassment_score,
            )

        monkeypatch.setattr(
            "app.services.db_service.crud2.create_incident_scores", fake
        )
        from app.services import db_service as db
        db.create_incident_scores(uuid.uuid4())
        assert captured["neutral_score"]   == 0.0
        assert captured["burnout_score"]   == 0.0
        assert captured["harassment_score"] == 0.0