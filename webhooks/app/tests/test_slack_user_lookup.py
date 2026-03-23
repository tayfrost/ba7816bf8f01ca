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
        assert last == "unknown"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_timeout_returns_defaults(self, mock_client_cls):
        import httpx
        from app.services.slack_user_service import lookup_slack_user

        _mock_httpx_client(mock_client_cls,
                           side_effect=httpx.TimeoutException("timed out"))

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == "unknown"
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
        assert last == "unknown"
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
        assert last == "unknown"
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
    @patch("app.services.slack_user_service.time")
    def test_cache_expires_after_ttl(self, mock_time, mock_fetch):
        from app.services.slack_user_service import lookup_slack_user, _CACHE_TTL

        mock_fetch.return_value = ("Vishal", "Thakwani", "v@example.com")
        mock_time.side_effect = [100.0, 100.0, 100.0 + _CACHE_TTL + 1, 100.0 + _CACHE_TTL + 1]

        lookup_slack_user("xoxb-token", "U123")
        lookup_slack_user("xoxb-token", "U123")

        assert mock_fetch.call_count == 2


class TestSlackRetryHeader:

    def test_retry_header_returns_200_immediately(self):
        from fastapi.testclient import TestClient
        import json

        from app.controllers.slack_controller import router
        from fastapi import FastAPI
        test_app = FastAPI()
        test_app.include_router(router)
        client = TestClient(test_app)

        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {"type": "message", "user": "U1", "text": "help", "ts": "1", "channel": "C1"},
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

    def _make_filter_result(self, is_risk=True, category="burnout", severity="early"):
        mock_result = MagicMock()
        mock_result.is_risk = is_risk
        mock_result.category = category
        mock_result.severity = severity
        return mock_result

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_new_user_passes_email_to_create(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = self._make_filter_result()
        mock_lookup.return_value = ("Vishal", "Thakwani", "vishal@example.com")

        mock_workspace = MagicMock()
        mock_workspace.company_id = 1
        mock_workspace.access_token = "xoxb-test"
        mock_db.get_workspace_by_team_id.return_value = mock_workspace
        mock_db.get_slack_account.return_value = None

        mock_user = MagicMock()
        mock_user.user_id = "uid-new"
        mock_db.create_viewer_seat.return_value = mock_user

        mock_incident = MagicMock()
        mock_incident.message_id = "mid-1"
        mock_db.create_message_incident.return_value = mock_incident

        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is True
        mock_lookup.assert_called_once_with("xoxb-test", "U123")
        mock_db.create_viewer_seat.assert_called_once_with(1, display_name="Vishal Thakwani")
        mock_db.create_slack_account.assert_called_once_with(
            1, "T123", "U123", "uid-new", email="vishal@example.com",
        )
        mock_db.create_message_incident.assert_called_once()
        mock_db.create_incident_scores.assert_called_once()

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_existing_user_backfills_email(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = self._make_filter_result()
        mock_lookup.return_value = ("Vishal", "Thakwani", "vishal@example.com")

        mock_workspace = MagicMock()
        mock_workspace.company_id = 1
        mock_workspace.access_token = "xoxb-test"
        mock_db.get_workspace_by_team_id.return_value = mock_workspace

        existing = MagicMock()
        existing.user_id = "uid-existing"
        existing.email = None
        mock_db.get_slack_account.return_value = existing

        mock_incident = MagicMock()
        mock_incident.message_id = "mid-2"
        mock_db.create_message_incident.return_value = mock_incident

        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is True
        mock_db.update_slack_account_email.assert_called_once_with("T123", "U123", "vishal@example.com")
        mock_db.create_viewer_seat.assert_not_called()

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_handles_unknown_lookup_gracefully(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = self._make_filter_result()
        mock_lookup.return_value = ("unknown", "unknown", None)

        mock_workspace = MagicMock()
        mock_workspace.company_id = 1
        mock_workspace.access_token = "xoxb-test"
        mock_db.get_workspace_by_team_id.return_value = mock_workspace
        mock_db.get_slack_account.return_value = None

        mock_user = MagicMock()
        mock_user.user_id = "uid-fallback"
        mock_db.create_viewer_seat.return_value = mock_user

        mock_incident = MagicMock()
        mock_incident.message_id = "mid-3"
        mock_db.create_message_incident.return_value = mock_incident

        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is True
        mock_db.create_viewer_seat.assert_called_once_with(1, display_name="Slack user U123")
        mock_db.create_slack_account.assert_called_once_with(
            1, "T123", "U123", "uid-fallback", email=None,
        )

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_lookup_not_called_when_filter_rejects(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = None

        payload = {
            "type": "event_callback", "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "lunch?", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is False
        mock_lookup.assert_not_called()
        mock_db.get_slack_account.assert_not_called()
