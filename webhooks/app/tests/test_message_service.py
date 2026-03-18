"""
Isolated unit tests for message_service.py

Covers the full Slack and Gmail message processing pipelines including
filter gating, viewer seat creation, incident + scores storage, and
history cursor advancement. No real DB, gRPC, or Gmail API calls.

Run with:
    pytest tests/test_message_service.py -v
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


def _make_filter_result(is_risk=True, category="stress", severity="early"):
    from app.services.filter_service import FilterResult
    return FilterResult(
        is_risk=is_risk,
        category=category,
        category_confidence=0.9,
        severity=severity,
        severity_confidence=0.85,
    )


def _make_workspace(**kw):
    return SimpleNamespace(
        slack_workspace_id=1, company_id=1, team_id="T123",
        access_token="xoxb-token", revoked_at=None, **kw
    )


def _make_user(**kw):
    return SimpleNamespace(
        user_id=uuid.uuid4(), company_id=1, role="viewer",
        status="active", display_name="Test User", **kw
    )


def _make_slack_account(**kw):
    return SimpleNamespace(
        company_id=1, team_id="T123", slack_user_id="U999",
        user_id=uuid.uuid4(), email=None, **kw
    )


def _make_mailbox(**kw):
    defaults = dict(
        google_mailbox_id=10, company_id=1, user_id=uuid.uuid4(),
        email_address="emp@example.com",
        token_json={"token": "t", "refresh_token": "r"},
        last_history_id="100", watch_expiration=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_incident(**kw):
    defaults = dict(
        message_id=uuid.uuid4(), company_id=1, user_id=uuid.uuid4(),
        source="slack", sent_at=_utcnow(), content_raw={},
        conversation_id=None,
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
                  new_user=None, incident=None):
        workspace  = workspace  or _make_workspace()
        new_user   = new_user   or _make_user()
        incident   = incident   or _make_incident()
        monkeypatch.setattr(
            "app.services.message_service.db.get_workspace_by_team_id",
            lambda tid: workspace,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.get_slack_account",
            lambda tid, uid: existing_account,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: new_user,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_slack_account",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: incident,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        return new_user, incident

    # ── filter gating ─────────────────────────────────────────────

    def test_drops_when_filter_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: None
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(), "") is False

    def test_drops_when_is_risk_false(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=False),
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(), "") is False

    def test_stores_when_is_risk_true(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        self._patch_db(monkeypatch)
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(), "") is True

    # ── event type guards ─────────────────────────────────────────

    def test_drops_bot_messages(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(
            _slack_payload(subtype="bot_message"), ""
        ) is False

    def test_drops_non_event_callback_type(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        payload        = _slack_payload()
        payload["type"] = "block_actions"
        from app.services.message_service import process_slack_message
        assert process_slack_message(payload, "") is False

    def test_drops_non_message_event_type(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        payload                 = _slack_payload()
        payload["event"]["type"] = "reaction_added"
        from app.services.message_service import process_slack_message
        assert process_slack_message(payload, "") is False

    # ── workspace lookup ──────────────────────────────────────────

    def test_drops_when_workspace_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.get_workspace_by_team_id",
            lambda tid: None,
        )
        from app.services.message_service import process_slack_message
        assert process_slack_message(_slack_payload(), "") is False

    # ── user seat creation ────────────────────────────────────────

    def test_creates_viewer_seat_for_new_user(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        new_user, _ = self._patch_db(monkeypatch, existing_account=None)
        captured    = {}

        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: (
                captured.update(display_name=display_name) or new_user
            ),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(user="U999"), "")
        assert "Slack user U999" in captured["display_name"]

    def test_reuses_existing_account_user_id(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        existing = _make_slack_account()
        captured = {}
        self._patch_db(monkeypatch, existing_account=existing)

        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda cid, user_id, *a, **kw: (
                captured.update(user_id=user_id) or _make_incident()
            ),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["user_id"] == existing.user_id

    def test_does_not_create_seat_for_existing_user(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        existing = _make_slack_account()
        self._patch_db(monkeypatch, existing_account=existing)
        seat_created = []
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda *a, **kw: seat_created.append(True) or _make_user(),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert seat_created == []

    # ── incident creation ─────────────────────────────────────────

    def test_incident_source_is_slack(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda cid, uid, source, *a, **kw: (
                captured.update(source=source) or _make_incident()
            ),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["source"] == "slack"

    def test_incident_conversation_id_is_channel(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: (
                captured.update(conversation_id=kw.get("conversation_id"))
                or _make_incident()
            ),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(channel="C-GENERAL"), "")
        assert captured["conversation_id"] == "C-GENERAL"

    def test_incident_content_raw_has_text(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(),
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: (
                captured.update(content_raw=kw.get("content_raw"))
                or _make_incident()
            ),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(text="some message"), "")
        assert captured["content_raw"] == {"text": "some message"}

    # ── scores creation ───────────────────────────────────────────

    def test_scores_created_with_category_and_severity(self, monkeypatch):
        result = _make_filter_result(category="harassment", severity="middle")
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: result
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda mid, **kw: captured.update(kw),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["predicted_category"] == "harassment"
        assert captured["predicted_severity"] == 2  # "middle" → 2

    def test_severity_map_none_is_zero(self, monkeypatch):
        result = _make_filter_result(severity="none")
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: result
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda mid, **kw: captured.update(kw),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["predicted_severity"] == 0

    def test_severity_map_late_is_three(self, monkeypatch):
        result = _make_filter_result(severity="late")
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: result
        )
        self._patch_db(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda mid, **kw: captured.update(kw),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["predicted_severity"] == 3

    def test_scores_uses_incident_message_id(self, monkeypatch):
        result = _make_filter_result()
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: result
        )
        incident = _make_incident()
        self._patch_db(monkeypatch, incident=incident)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda mid, **kw: captured.update(message_id=mid),
        )
        from app.services.message_service import process_slack_message
        process_slack_message(_slack_payload(), "")
        assert captured["message_id"] == incident.message_id


# ── process_gmail_event ───────────────────────────────────────────

class TestProcessGmailEvent:

    def _patch_fetch(self, monkeypatch, messages, latest_id="101"):
        monkeypatch.setattr(
            "app.services.message_service._fetch_new_messages",
            lambda acc, email: (messages, latest_id),
        )

    def _patch_db(self, monkeypatch, incident=None):
        incident = incident or _make_incident(source="gmail")
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: incident,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        return incident

    # ── payload decoding ──────────────────────────────────────────

    def test_returns_false_on_malformed_payload(self, monkeypatch):
        from app.services.message_service import process_gmail_event
        assert process_gmail_event({"message": {"data": "!!!"}}) is False

    def test_returns_false_when_email_missing(self, monkeypatch):
        data = base64.b64encode(json.dumps({"historyId": "123"}).encode()).decode()
        from app.services.message_service import process_gmail_event
        assert process_gmail_event({"message": {"data": data}}) is False

    def test_returns_false_when_no_mailbox(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: None,
        )
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is False

    # ── baseline historyId ────────────────────────────────────────

    def test_stores_baseline_on_first_notification(self, monkeypatch):
        account  = _make_mailbox(last_history_id=None)
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(mailbox_id=mid, history_id=hid),
        )
        from app.services.message_service import process_gmail_event
        result = process_gmail_event(_pubsub_payload(history_id="55555"))
        assert result is False
        assert captured["mailbox_id"] == account.google_mailbox_id
        assert captured["history_id"] == "55555"

    # ── history cursor ────────────────────────────────────────────

    def test_history_id_always_advances(self, monkeypatch):
        account  = _make_mailbox(last_history_id="100")
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [], latest_id="999")
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(history_id=hid),
        )
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=False),
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["history_id"] == "999"

    def test_history_advances_even_when_no_messages_stored(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()], latest_id="200")
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=False),
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda mid, hid: captured.update(history_id=hid),
        )
        from app.services.message_service import process_gmail_event
        result = process_gmail_event(_pubsub_payload())
        assert result is False
        assert captured["history_id"] == "200"

    # ── filter gating ─────────────────────────────────────────────

    def test_skips_message_when_filter_returns_none(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message", lambda t: None
        )
        self._patch_db(monkeypatch)
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is False

    def test_skips_message_when_not_a_risk(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=False),
        )
        self._patch_db(monkeypatch)
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is False

    def test_stores_when_filter_flags_message(self, monkeypatch):
        account  = _make_mailbox(last_history_id="100")
        incident = _make_incident(source="gmail")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        self._patch_db(monkeypatch, incident=incident)
        from app.services.message_service import process_gmail_event
        assert process_gmail_event(_pubsub_payload()) is True

    # ── incident creation ─────────────────────────────────────────

    def test_incident_source_is_gmail(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda cid, uid, source, *a, **kw: (
                captured.update(source=source) or _make_incident()
            ),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["source"] == "gmail"

    def test_incident_conversation_id_is_gmail(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: (
                captured.update(conversation_id=kw.get("conversation_id"))
                or _make_incident()
            ),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["conversation_id"] == "gmail"

    def test_content_raw_includes_subject_from_to(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message(
            body_text="urgent", subject="Re: project",
            from_="boss@co.com", to="emp@co.com",
        )])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: (
                captured.update(content_raw=kw.get("content_raw"))
                or _make_incident()
            ),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["content_raw"]["subject"] == "Re: project"
        assert captured["content_raw"]["from"]    == "boss@co.com"
        assert captured["content_raw"]["to"]      == "emp@co.com"

    # ── scores creation ───────────────────────────────────────────

    def test_scores_created_after_gmail_incident(self, monkeypatch):
        account  = _make_mailbox(last_history_id="100")
        incident = _make_incident()
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message()])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(category="depression", severity="late"),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: incident,
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda mid, **kw: captured.update(message_id=mid, **kw),
        )
        from app.services.message_service import process_gmail_event
        process_gmail_event(_pubsub_payload())
        assert captured["message_id"]         == incident.message_id
        assert captured["predicted_category"] == "depression"
        assert captured["predicted_severity"] == 3

    def test_multiple_risk_messages_all_stored(self, monkeypatch):
        account = _make_mailbox(last_history_id="100")
        monkeypatch.setattr(
            "app.services.message_service._get_mailbox_by_email_any_company",
            lambda email: account,
        )
        self._patch_fetch(monkeypatch, [_fake_message("msg1"), _fake_message("msg2")])
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: _make_filter_result(is_risk=True),
        )
        incident_calls = []
        scores_calls   = []
        monkeypatch.setattr(
            "app.services.message_service.db.set_google_mailbox_history_id",
            lambda *a: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: incident_calls.append(1) or _make_incident(),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: scores_calls.append(1),
        )
        from app.services.message_service import process_gmail_event
        result = process_gmail_event(_pubsub_payload())
        assert result is True
        assert len(incident_calls) == 2
        assert len(scores_calls)   == 2