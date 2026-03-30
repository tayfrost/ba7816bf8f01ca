"""
Tests for Slack user email lookup, caching, retry handling,
and integration with process_slack_message.
"""

import pytest
from unittest.mock import patch, MagicMock
from time import time


def _mock_httpx_client(mock_client_cls, json_response=None, side_effect=None):
    """Helper to wire up the httpx.Client context-manager mock."""
    mock_inner = MagicMock()
    if side_effect:
        mock_inner.get.side_effect = side_effect
    else:
        mock_resp = MagicMock()
        mock_resp.json.return_value = json_response
        mock_resp.raise_for_status = MagicMock()
        mock_inner.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_inner)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_inner


class TestLookupSlackUser:

    def setup_method(self):
        import app.services.slack_user_service as svc
        svc._cache.clear()

    @patch("app.services.slack_user_service.httpx.Client")
    def test_successful_lookup_with_email(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {
                "id": "U123", "real_name": "Vishal Thakwani",
                "profile": {"first_name": "Vishal", "last_name": "Thakwani",
                             "email": "vishal@example.com"},
            },
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email == "vishal@example.com"

    @patch("app.services.slack_user_service.httpx.Client")
    def test_successful_lookup_without_email(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {
                "id": "U123", "real_name": "Vishal Thakwani",
                "profile": {"first_name": "Vishal", "last_name": "Thakwani"},
            },
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_api_returns_error(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {"ok": False, "error": "user_not_found"})

        first, last, email = lookup_slack_user("xoxb-token", "U999")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_timeout_returns_defaults(self, mock_client_cls):
        import httpx
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls,
                           side_effect=httpx.TimeoutException("timed out"))

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_fallback_to_real_name_when_no_first_last(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": "Vishal Thakwani", "profile": {}},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_single_word_real_name(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": "Madonna", "profile": {}},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Madonna"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_empty_string_email_coerced_to_none(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {
                "id": "U123", "real_name": "Test User",
                "profile": {"first_name": "Test", "last_name": "User", "email": ""},
            },
        })

        _, _, email = lookup_slack_user("xoxb-token", "U123")
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_http_429_rate_limit_returns_defaults(self, mock_client_cls):
        import httpx
        from app.services.slack_user_service import lookup_slack_user

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=mock_response)

        mock_inner = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = error
        mock_inner.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_inner)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_malformed_json_response_returns_defaults(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        mock_inner = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("No JSON: <html>502 Bad Gateway</html>")
        mock_inner.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_inner)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_null_profile_returns_real_name_fallback(self, mock_client_cls):
        """Slack can return explicit null for profile — must not AttributeError."""
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": "Ada Lovelace", "profile": None},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Ada"
        assert last == "Lovelace"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_whitespace_only_real_name_returns_defaults(self, mock_client_cls):
        """Whitespace real_name must not IndexError on empty split."""
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": "   ", "profile": {}},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_empty_profile_and_empty_real_name(self, mock_client_cls):
        """Both fallback paths fail — should return clean defaults."""
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": "", "profile": {}},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_null_real_name_returns_defaults(self, mock_client_cls):
        """Explicit null real_name must not AttributeError on .strip()."""
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls, {
            "ok": True,
            "user": {"id": "U123", "real_name": None, "profile": {}},
        })

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == ""
        assert email is None


class TestLookupCache:

    def setup_method(self):
        import app.services.slack_user_service as svc
        svc._cache.clear()

    @patch("app.services.slack_user_service._fetch_from_slack")
    def test_cache_avoids_duplicate_calls(self, mock_fetch):
        from app.services.slack_user_service import lookup_slack_user

        mock_fetch.return_value = ("Vishal", "Thakwani", "v@example.com")

        lookup_slack_user("xoxb-token", "U123")
        lookup_slack_user("xoxb-token", "U123")
        lookup_slack_user("xoxb-token", "U123")

        mock_fetch.assert_called_once()

    @patch("app.services.slack_user_service._fetch_from_slack")
    def test_failed_lookup_not_cached(self, mock_fetch):
        from app.services.slack_user_service import lookup_slack_user, _cache

        mock_fetch.return_value = ("unknown", "", None)

        lookup_slack_user("xoxb-token", "U404")
        assert "U404" not in _cache
        assert mock_fetch.call_count == 1

        lookup_slack_user("xoxb-token", "U404")
        assert mock_fetch.call_count == 2

    @patch("app.services.slack_user_service._fetch_from_slack")
    @patch("app.services.slack_user_service.time")
    def test_cache_expires_after_ttl(self, mock_time, mock_fetch):
        from app.services.slack_user_service import lookup_slack_user, _CACHE_TTL

        mock_fetch.return_value = ("Vishal", "Thakwani", "v@example.com")
        # Call 1: time() for cache write → 100.0
        # Call 2: time() for cache check in second lookup → expired
        # Call 3: time() for cache re-write → same expired time
        mock_time.side_effect = [100.0, 100.0 + _CACHE_TTL + 1, 100.0 + _CACHE_TTL + 1]

        lookup_slack_user("xoxb-token", "U123")
        lookup_slack_user("xoxb-token", "U123")

        assert mock_fetch.call_count == 2

    @patch("app.services.slack_user_service._fetch_from_slack")
    def test_single_word_name_user_is_cached(self, mock_fetch):
        """'Madonna' with last='' differs from _DEFAULT ('unknown','',None) so gets cached."""
        from app.services.slack_user_service import lookup_slack_user, _cache

        mock_fetch.return_value = ("Madonna", "", None)

        lookup_slack_user("xoxb-token", "UMADONNA")
        assert "UMADONNA" in _cache

        lookup_slack_user("xoxb-token", "UMADONNA")
        mock_fetch.assert_called_once()


class TestSlackRetryHeader:

    def test_retry_header_returns_200_immediately(self, monkeypatch):
        """Slack retries carry an X-Slack-Retry-Num header.
        The controller should return 200 immediately without processing."""
        import sys
        import json
        from unittest.mock import MagicMock

        stubs = [
            "backend", "backend.New_database",
            "backend.New_database.new_crud",
            "backend.New_database.new_oop",
        ]
        for mod_name in stubs:
            monkeypatch.setitem(sys.modules, mod_name, MagicMock())

        for mod_name, attrs in [
            ("app.services.db_service", {}),
            ("app.services.oauth_service", {"process_slack_oauth": MagicMock()}),
            ("app.services.message_service", {"process_slack_message": MagicMock()}),
        ]:
            stub = MagicMock(**attrs)
            monkeypatch.setitem(sys.modules, mod_name, stub)

        monkeypatch.delitem(sys.modules, "app.controllers.slack_controller", raising=False)

        from app.controllers.slack_controller import router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(router)
        client = TestClient(test_app)

        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {"type": "message", "user": "U1", "text": "help",
                      "ts": "1", "channel": "C1"},
        }
        resp = client.post(
            "/slack/events",
            content=json.dumps(payload),
            headers={
                "X-Slack-Retry-Num": "1",
                "X-Slack-Retry-Reason": "http_timeout",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestProcessSlackMessageWithLookup:
    """Integration tests verifying lookup_slack_user inside process_slack_message.

    Uses monkeypatch.setattr (matching test_message_service.py pattern) to
    avoid @patch-decorator import chain issues with backend.New_database deps.
    """

    def _make_filter_result(self, is_risk=True, category="burnout",
                            severity="early"):
        from app.services.filter_service import FilterResult
        return FilterResult(
            is_risk=is_risk, category=category,
            category_confidence=0.9, severity=severity,
            severity_confidence=0.85,
        )

    def _patch_all(self, monkeypatch, *, lookup_result=None,
                   existing_account=None):
        """Patch all external deps so process_slack_message runs in isolation."""
        from types import SimpleNamespace
        import uuid
        from datetime import datetime, timezone

        workspace = SimpleNamespace(
            slack_workspace_id=1, company_id=1, team_id="T123",
            access_token="xoxb-test", revoked_at=None,
        )
        new_user = SimpleNamespace(
            user_id=uuid.uuid4(), company_id=1, role="viewer",
            status="active", display_name="Test",
        )
        incident = SimpleNamespace(
            message_id=uuid.uuid4(), company_id=1,
            user_id=uuid.uuid4(), source="slack",
            sent_at=datetime.now(tz=timezone.utc),
            content_raw={}, conversation_id=None,
        )

        lookup = lookup_result or ("unknown", "", None)
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: lookup,
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
        monkeypatch.setattr(
            "app.services.message_service.db.create_message_incident",
            lambda *a, **kw: incident,
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_incident_scores",
            lambda *a, **kw: None,
        )
        return new_user, incident

    def test_new_user_passes_email_to_create(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: self._make_filter_result(),
        )
        new_user, _ = self._patch_all(
            monkeypatch,
            lookup_result=("Vishal", "Thakwani", "vishal@example.com"),
            existing_account=None,
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: (
                captured.update(display_name=display_name) or new_user
            ),
        )
        monkeypatch.setattr(
            "app.services.message_service.db.create_slack_account",
            lambda *a, **kw: captured.update(kw),
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is True
        assert captured["display_name"] == "Vishal Thakwani"
        assert captured.get("email") == "vishal@example.com"

    def test_existing_user_backfills_email(self, monkeypatch):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: self._make_filter_result(),
        )
        existing = SimpleNamespace(
            user_id="uid-existing", email=None,
            company_id=1, team_id="T123", slack_user_id="U123",
        )
        self._patch_all(
            monkeypatch,
            existing_account=existing,
            lookup_result=("Ada", "Lovelace", "ada@kcl.ac.uk"),
        )
        mock_update = MagicMock()
        monkeypatch.setattr(
            "app.services.message_service.db.update_slack_account_email",
            mock_update,
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is True
        mock_update.assert_called_once_with("T123", "U123", "ada@kcl.ac.uk")

    def test_handles_unknown_lookup_gracefully(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: self._make_filter_result(),
        )
        new_user, _ = self._patch_all(
            monkeypatch,
            lookup_result=("unknown", "", None),
            existing_account=None,
        )
        captured = {}
        monkeypatch.setattr(
            "app.services.message_service.db.create_viewer_seat",
            lambda cid, display_name: (
                captured.update(display_name=display_name) or new_user
            ),
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is True
        assert captured["display_name"] == "Slack user U123"

    def test_existing_email_not_overwritten(self, monkeypatch):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: self._make_filter_result(),
        )
        existing = SimpleNamespace(
            user_id="uid-existing", email="already@example.com",
            company_id=1, team_id="T123", slack_user_id="U123",
        )
        self._patch_all(
            monkeypatch,
            existing_account=existing,
            lookup_result=("Ada", "Lovelace", "new@example.com"),
        )
        mock_update = MagicMock()
        monkeypatch.setattr(
            "app.services.message_service.db.update_slack_account_email",
            mock_update,
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is True
        mock_update.assert_not_called()

    def test_lookup_not_called_when_filter_returns_none(self, monkeypatch):
        lookup_called = []
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: None,
        )
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: lookup_called.append(True) or ("x", "y", None),
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "lunch?",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is False
        assert lookup_called == []

    def test_lookup_not_called_when_is_risk_false(self, monkeypatch):
        lookup_called = []
        monkeypatch.setattr(
            "app.services.message_service.filter_message",
            lambda t: self._make_filter_result(is_risk=False),
        )
        monkeypatch.setattr(
            "app.services.message_service.lookup_slack_user",
            lambda token, uid: lookup_called.append(True) or ("x", "y", None),
        )

        from app.services.message_service import process_slack_message
        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "lunch?",
                      "ts": "1", "channel": "C1"},
        }
        result = process_slack_message(payload, "1")

        assert result is False
        assert lookup_called == []
