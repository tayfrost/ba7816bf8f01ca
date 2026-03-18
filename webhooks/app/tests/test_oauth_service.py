"""
Isolated unit tests for oauth_service.py

Covers Slack OAuth (create vs update workspace) and Gmail OAuth
(first connect vs reconnect, watch registration, historyId storage).
All Google API calls and DB operations are monkeypatched.

Run with:
    pytest tests/test_oauth_service.py -v
"""

import uuid
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ── Helpers ───────────────────────────────────────────────────────

def _make_workspace(**kw):
    return SimpleNamespace(
        slack_workspace_id=1, company_id=1, team_id="T123",
        access_token="xoxb-token", revoked_at=None, **kw
    )


def _make_user(**kw):
    return SimpleNamespace(
        user_id=uuid.uuid4(), company_id=1, role="viewer",
        status="active", display_name="emp@example.com", **kw
    )


def _make_mailbox(**kw):
    return SimpleNamespace(
        google_mailbox_id=10, company_id=1, user_id=uuid.uuid4(),
        email_address="emp@example.com",
        token_json={"token": "t", "refresh_token": "r"},
        last_history_id=None, watch_expiration=None, **kw
    )


def _patch_google(monkeypatch, email="emp@example.com",
                  history_id="12345", expiration="9999999999000"):
    """Patch _build_flow and the Gmail API build() call."""
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = json.dumps(
        {"token": "t", "refresh_token": "r"}
    )

    mock_flow = MagicMock()
    mock_flow.credentials = mock_creds
    monkeypatch.setattr("app.services.oauth_service._build_flow",
                        lambda: mock_flow)

    mock_service = MagicMock()
    mock_service.users().getProfile().execute.return_value = {
        "emailAddress": email
    }
    mock_service.users().watch().execute.return_value = {
        "historyId": history_id,
        "expiration": expiration,
    }
    monkeypatch.setattr(
        "app.services.oauth_service.build",
        lambda *a, **kw: mock_service,
    )
    return mock_flow, mock_service


# ── process_slack_oauth ───────────────────────────────────────────

class TestProcessSlackOauth:

    def test_creates_workspace_when_none_exists(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_workspace_by_team_id",
            lambda tid: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_workspace",
            lambda cid, tid, token: captured.update(
                company_id=cid, team_id=tid, access_token=token
            ),
        )
        from app.services.oauth_service import process_slack_oauth
        result = process_slack_oauth({
            "ok": True, "team": {"id": "T123"},
            "access_token": "xoxb-new", "_company_id": 1,
        })
        assert result.team_id          == "T123"
        assert captured["company_id"]   == 1
        assert captured["team_id"]      == "T123"
        assert captured["access_token"] == "xoxb-new"

    def test_updates_token_when_workspace_exists(self, monkeypatch):
        existing = _make_workspace()
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_workspace_by_team_id",
            lambda tid: existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_workspace_token",
            lambda tid, token: captured.update(access_token=token),
        )
        from app.services.oauth_service import process_slack_oauth
        process_slack_oauth({
            "ok": True, "team": {"id": "T123"},
            "access_token": "xoxb-refreshed", "_company_id": 1,
        })
        assert captured["access_token"] == "xoxb-refreshed"

    def test_does_not_create_workspace_on_reinstall(self, monkeypatch):
        existing     = _make_workspace()
        create_calls = []
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_workspace_by_team_id",
            lambda tid: existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_workspace",
            lambda *a: create_calls.append(1),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_workspace_token",
            lambda *a: None,
        )
        from app.services.oauth_service import process_slack_oauth
        process_slack_oauth({
            "ok": True, "team": {"id": "T123"},
            "access_token": "xoxb-r", "_company_id": 1,
        })
        assert create_calls == []

    def test_raises_on_slack_error_response(self, monkeypatch):
        from app.services.oauth_service import process_slack_oauth
        with pytest.raises(ValueError, match="invalid_code"):
            process_slack_oauth({
                "ok": False, "error": "invalid_code", "_company_id": 1
            })

    def test_raises_when_company_id_missing(self, monkeypatch):
        from app.services.oauth_service import process_slack_oauth
        with pytest.raises(ValueError, match="company_id missing"):
            process_slack_oauth({
                "ok": True, "team": {"id": "T123"}, "access_token": "x"
            })

    def test_raises_when_company_id_is_zero(self, monkeypatch):
        from app.services.oauth_service import process_slack_oauth
        with pytest.raises(ValueError, match="company_id missing"):
            process_slack_oauth({
                "ok": True, "team": {"id": "T123"},
                "access_token": "x", "_company_id": 0,
            })

    def test_returns_workspace_credentials_schema(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_workspace_by_team_id",
            lambda tid: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_workspace",
            lambda *a: None,
        )
        from app.services.oauth_service import process_slack_oauth
        from app.schemas.workspace_schema import WorkspaceCredentials
        result = process_slack_oauth({
            "ok": True, "team": {"id": "T999"},
            "access_token": "xoxb-x", "_company_id": 5,
        })
        assert isinstance(result, WorkspaceCredentials)
        assert result.team_id      == "T999"
        assert result.access_token == "xoxb-x"


# ── process_gmail_oauth ───────────────────────────────────────────

class TestProcessGmailOauth:

    def _stub_db_first_connect(self, monkeypatch, new_user=None, new_mailbox=None):
        new_user    = new_user    or _make_user()
        new_mailbox = new_mailbox or _make_mailbox(google_mailbox_id=5,
                                                   user_id=new_user.user_id)
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_viewer_seat",
            lambda cid, display_name: new_user,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_google_mailbox",
            lambda *a: new_mailbox,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        return new_user, new_mailbox

    def test_returns_email_address(self, monkeypatch):
        _patch_google(monkeypatch, email="emp@example.com")
        self._stub_db_first_connect(monkeypatch)
        from app.services.oauth_service import process_gmail_oauth
        result = process_gmail_oauth("auth-code", company_id=1)
        assert result == "emp@example.com"

    def test_creates_viewer_seat_on_first_connect(self, monkeypatch):
        _patch_google(monkeypatch)
        new_user = _make_user()
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_viewer_seat",
            lambda cid, display_name: (
                captured.update(company_id=cid, display_name=display_name)
                or new_user
            ),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_google_mailbox",
            lambda *a: _make_mailbox(user_id=new_user.user_id),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["company_id"]   == 1
        assert captured["display_name"] == "emp@example.com"

    def test_mailbox_created_with_correct_user_id(self, monkeypatch):
        _patch_google(monkeypatch)
        new_user = _make_user()
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_viewer_seat",
            lambda cid, display_name: new_user,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_google_mailbox",
            lambda cid, user_id, email, token: (
                captured.update(user_id=user_id)
                or _make_mailbox(user_id=user_id)
            ),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["user_id"] == new_user.user_id

    def test_does_not_create_seat_on_reconnect(self, monkeypatch):
        _patch_google(monkeypatch)
        existing     = _make_mailbox(google_mailbox_id=7)
        seat_created = []
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_viewer_seat",
            lambda *a: seat_created.append(1) or _make_user(),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_token",
            lambda *a: existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert seat_created == []

    def test_updates_token_on_reconnect(self, monkeypatch):
        _patch_google(monkeypatch)
        existing = _make_mailbox(google_mailbox_id=7)
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_token",
            lambda mid, token: captured.update(mailbox_id=mid) or existing,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["mailbox_id"] == existing.google_mailbox_id

    def test_history_id_stored_after_watch(self, monkeypatch):
        _patch_google(monkeypatch, history_id="99999")
        _, mailbox = self._stub_db_first_connect(monkeypatch)
        captured   = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(mailbox_id=mid, history_id=hid),
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["mailbox_id"] == mailbox.google_mailbox_id
        assert captured["history_id"] == "99999"

    def test_watch_expiration_stored(self, monkeypatch):
        _patch_google(monkeypatch, expiration="9999999999000")
        _, mailbox = self._stub_db_first_connect(monkeypatch)
        captured   = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda mid, exp: captured.update(mailbox_id=mid, expiry=exp),
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["mailbox_id"] == mailbox.google_mailbox_id
        assert isinstance(captured["expiry"], datetime)

    def test_watch_uses_mailbox_pk_not_user_id(self, monkeypatch):
        _patch_google(monkeypatch)
        mailbox  = _make_mailbox(google_mailbox_id=42)
        captured = {}
        monkeypatch.setattr(
            "app.services.oauth_service.db.get_google_mailbox_by_email",
            lambda cid, email: None,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_viewer_seat",
            lambda *a: _make_user(),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.create_google_mailbox",
            lambda *a: mailbox,
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(mailbox_id=mid),
        )
        monkeypatch.setattr(
            "app.services.oauth_service.db.update_google_mailbox_watch_expiration",
            lambda *a: None,
        )
        from app.services.oauth_service import process_gmail_oauth
        process_gmail_oauth("auth-code", company_id=1)
        assert captured["mailbox_id"] == 42