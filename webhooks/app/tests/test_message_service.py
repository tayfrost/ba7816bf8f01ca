"""
Unit tests for message_service.py

Covers Slack and Gmail processing pipelines:
- user resolution / account registration
- fire-and-forget dispatch to filter (dispatch_to_filter called with correct meta)
- early-exit conditions (bad payload, missing workspace, etc.)

No real DB, gRPC, or Gmail API calls.
"""

import uuid
import json
import base64
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


# ── Helpers ───────────────────────────────────────────────────────

def _utcnow():
    return datetime.now(tz=timezone.utc)


def _make_workspace(**kw):
    defaults = dict(
        slack_workspace_id=1, company_id=1, team_id="T123",
        access_token="xoxb-token", revoked_at=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_user(**kw):
    defaults = dict(
        user_id=uuid.uuid4(), company_id=1, role="viewer",
        status="active", display_name="Test User",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_slack_account(**kw):
    defaults = dict(
        company_id=1, team_id="T123", slack_user_id="U999",
        user_id=uuid.uuid4(), email=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_mailbox(**kw):
    defaults = dict(
        google_mailbox_id=10, company_id=1, user_id=uuid.uuid4(),
        email_address="emp@example.com",
        token_json={"token": "t", "refresh_token": "r"},
        last_history_id="100", watch_expiration=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _slack_payload(team_id="T123", user="U999", text="hello", channel="C1",
                   subtype=None):
    event = {
        "type": "message", "user": user,
        "text": text, "ts": "1700000000.000", "channel": channel,
    }
    if subtype:
        event["subtype"] = subtype
    return {"type": "event_callback", "team_id": team_id, "event": event}


def _pubsub_payload(email="emp@example.com", history_id="55555"):
    data = base64.b64encode(
        json.dumps({"emailAddress": email, "historyId": history_id}).encode()
    ).decode()
    return {"message": {"data": data}}


def _raw_body(text="concerning text"):
    return base64.urlsafe_b64encode(text.encode()).decode()


def _fake_message(body_text="concerning text", internal_date="1700000000000",
                  subject="Test", from_="a@b.com", to="c@d.com"):
    return {
        "payload": {
            "mimeType": "text/plain",
            "body":     {"data": _raw_body(body_text)},
            "headers":  [
                {"name": "Subject", "value": subject},
                {"name": "From",    "value": from_},
                {"name": "To",      "value": to},
            ],
        },
        "internalDate": internal_date,
    }


# ── process_slack_message ─────────────────────────────────────────

class TestProcessSlackMessage:

    def _patch_db(self, monkeypatch, workspace=None, existing_account=None,
                  new_user=None):
        workspace = workspace or _make_workspace()
        new_user  = new_user  or _make_user()
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: ("unknown", "", None),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.get_workspace_by_team_id",
            lambda tid: workspace,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.get_slack_account",
            lambda tid, uid: existing_account,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.update_slack_account_email",
            lambda *a, **kw: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: new_user,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_slack_account",
            lambda *a, **kw: None,
        )
        return new_user

    # ── early exits ───────────────────────────────────────────────

    def test_drops_non_event_callback(self, monkeypatch):
        from app.services.message_service import process_slack_message
        payload = _slack_payload()
        payload["type"] = "block_actions"
        assert process_slack_message(payload, "") is False

    def test_drops_non_message_event(self, monkeypatch):
        from app.services.message_service import process_slack_message
        payload = _slack_payload()
        payload["event"]["type"] = "reaction_added"
        assert process_slack_message(payload, "") is False

    def test_drops_bot_messages(self, monkeypatch):
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(subtype="bot_message"), "") is False

    def test_drops_when_workspace_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.db.get_workspace_by_team_id",
            lambda tid: None,
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(), "") is False

    # ── dispatch ──────────────────────────────────────────────────

    def test_dispatches_and_returns_true(self, monkeypatch):
        self._patch_db(monkeypatch)
        dispatched = {}
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: dispatched.update(meta=meta, text=text),
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(text="hi"), "") is True
        assert dispatched["text"] == "hi"

    def test_dispatch_meta_contains_required_fields(self, monkeypatch):
        new_user = _make_user()
        self._patch_db(monkeypatch, new_user=new_user)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: captured.update(meta),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(user="U999", channel="C-GENERAL"), "")
        assert captured["source"]        == "slack"
        assert captured["user_id"]       == str(new_user.user_id)
        assert captured["company_id"]    == 1
        assert captured["slack_user_id"] == "U999"
        assert captured["conversation_id"] == "C-GENERAL"

    # ── user resolution ───────────────────────────────────────────

    def test_creates_viewer_seat_for_new_user(self, monkeypatch):
        self._patch_db(monkeypatch, existing_account=None)
        seat_created = []
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: seat_created.append(1) or _make_user(),
        )
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert seat_created == [1]

    def test_reuses_existing_account_user_id(self, monkeypatch):
        existing = _make_slack_account()
        self._patch_db(monkeypatch, existing_account=existing)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: captured.update(meta),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["user_id"] == str(existing.user_id)

    def test_does_not_create_seat_for_existing_user(self, monkeypatch):
        existing = _make_slack_account()
        self._patch_db(monkeypatch, existing_account=existing)
        seat_created = []
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda *a, **kw: seat_created.append(1) or _make_user(),
        )
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert seat_created == []

    def test_email_backfill_on_existing_account(self, monkeypatch):
        from unittest.mock import MagicMock
        existing = _make_slack_account(email=None)
        self._patch_db(monkeypatch, existing_account=existing)
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: ("Ada", "Lovelace", "ada@kcl.ac.uk"),
        )
        mock_update = MagicMock()
        monkeypatch.setattr(
            "app.services.message_service.db.update_slack_account_email",
            mock_update,
        )
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        mock_update.assert_called_once_with("T123", "U999", "ada@kcl.ac.uk")

    def test_no_backfill_when_existing_email_present(self, monkeypatch):
        from unittest.mock import MagicMock
        existing = _make_slack_account(email="old@example.com")
        self._patch_db(monkeypatch, existing_account=existing)
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: ("Ada", "Lovelace", "ada@kcl.ac.uk"),
        )
        mock_update = MagicMock()
        monkeypatch.setattr(
            "app.services.message_service.db.update_slack_account_email",
            mock_update,
        )
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        mock_update.assert_not_called()

    def test_email_included_in_dispatch_meta(self, monkeypatch):
        self._patch_db(monkeypatch, existing_account=None)
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: ("Ada", "Lovelace", "ada@kcl.ac.uk"),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: _make_user(),
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: captured.update(meta),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["email"] == "ada@kcl.ac.uk"


# ── process_gmail_event ───────────────────────────────────────────

class TestProcessGmailEvent:

    def _patch_fetch(self, monkeypatch, messages, latest_id="101"):
        monkeypatch.setattr(
            "app.services.message_service._fetch_new_messages",
            lambda acc, email: (messages, latest_id),
        )

    def _patch_db(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )

    # ── early exits ───────────────────────────────────────────────

    def test_returns_false_on_malformed_payload(self, monkeypatch):
        from app.services.message_service import process_gmail_event
        assert process_gmail_event({"message": {"data": "!!!"}}) is False

    def test_returns_false_when_email_missing(self, monkeypatch):
        data = base64.b64encode(json.dumps({"historyId": "123"}).encode()).decode()
        from app.services.message_service import process_gmail_event
        assert process_gmail_event({"message": {"data": data}}) is False

    def test_returns_false_when_no_mailbox(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: None,
        )
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is False

    def test_stores_baseline_on_first_notification(self, monkeypatch):
        account  = _make_mailbox(last_history_id=None)
        captured = {}
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: account,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(mailbox_id=mid, history_id=hid),
        )
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload(history_id="55555")) is False
        assert captured["history_id"] == "55555"

    # ── dispatch ─────────────────────────────────────────────────

    def test_dispatches_each_message(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message("msg1"), _fake_message("msg2")])
        self._patch_db(monkeypatch)
        calls = []
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: calls.append(text),
        )
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is True
        assert len(calls) == 2

    def test_dispatch_meta_contains_required_fields(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message(
            subject="Re: project", from_="boss@co.com", to="emp@co.com"
        )])
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: captured.update(meta),
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload(email="emp@example.com"))
        assert captured["source"]          == "gmail"
        assert captured["user_id"]         == str(account.user_id)
        assert captured["company_id"]      == account.company_id
        assert captured["email"]           == "emp@example.com"
        assert captured["subject"]         == "Re: project"
        assert captured["from"]            == "boss@co.com"
        assert captured["conversation_id"] == "gmail"

    def test_returns_false_when_no_messages(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [])
        self._patch_db(monkeypatch)
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is False

    def test_history_id_advances(self, monkeypatch):
        account  = _make_mailbox(last_history_id="100")
        captured = {}
        monkeypatch.setattr(
            "app.services.db_service.get_mailbox_by_email_global",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [], latest_id="999")
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(history_id=hid),
        )
        monkeypatch.setattr(
            "app.services.message_service.dispatch_to_filter",
            lambda meta, text: None,
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["history_id"] == "999"
