"""
Tests for Slack user email lookup and integration with process_slack_message.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestLookupSlackUser:

    @patch("app.services.slack_user_service.httpx.Client")
    def test_successful_lookup_with_email(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "user": {
                "id": "U123",
                "real_name": "Vishal Thakwani",
                "profile": {
                    "first_name": "Vishal",
                    "last_name": "Thakwani",
                    "email": "vishal@example.com",
                },
            },
        }
        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(get=MagicMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email == "vishal@example.com"

    @patch("app.services.slack_user_service.httpx.Client")
    def test_successful_lookup_without_email(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "user": {
                "id": "U123",
                "real_name": "Vishal Thakwani",
                "profile": {
                    "first_name": "Vishal",
                    "last_name": "Thakwani",
                },
            },
        }
        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(get=MagicMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_api_returns_error(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "user_not_found"}
        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(get=MagicMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U999")
        assert first == "unknown"
        assert last == "unknown"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_timeout_returns_defaults(self, mock_client_cls):
        import httpx
        from app.services.slack_user_service import lookup_slack_user

        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(
                get=MagicMock(side_effect=httpx.TimeoutException("timed out"))
            )
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "unknown"
        assert last == "unknown"
        assert email is None

    @patch("app.services.slack_user_service.httpx.Client")
    def test_fallback_to_real_name_when_no_first_last(self, mock_client_cls):
        from app.services.slack_user_service import lookup_slack_user

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "user": {
                "id": "U123",
                "real_name": "Vishal Thakwani",
                "profile": {},
            },
        }
        mock_client_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(get=MagicMock(return_value=mock_resp))
        )
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        first, last, email = lookup_slack_user("xoxb-token", "U123")
        assert first == "Vishal"
        assert last == "Thakwani"
        assert email is None


class TestProcessSlackMessageWithLookup:

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_passes_email_to_upsert(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = True
        mock_lookup.return_value = ("Vishal", "Thakwani", "vishal@example.com")

        mock_workspace = MagicMock()
        mock_workspace.company_id = 1
        mock_workspace.access_token = "xoxb-test"
        mock_db.get_workspace_by_team_id.return_value = mock_workspace

        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is True
        mock_lookup.assert_called_once_with("xoxb-test", "U123")
        mock_db.upsert_slack_user.assert_called_once_with(
            team_id="T123",
            slack_user_id="U123",
            name="Vishal",
            surname="Thakwani",
            email="vishal@example.com",
        )

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_handles_none_email_gracefully(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = True
        mock_lookup.return_value = ("unknown", "unknown", None)

        mock_workspace = MagicMock()
        mock_workspace.company_id = 1
        mock_workspace.access_token = "xoxb-test"
        mock_db.get_workspace_by_team_id.return_value = mock_workspace

        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "help", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is True
        mock_db.upsert_slack_user.assert_called_once_with(
            team_id="T123",
            slack_user_id="U123",
            name="unknown",
            surname="unknown",
            email=None,
        )

    @patch("app.services.message_service.db")
    @patch("app.services.message_service.lookup_slack_user")
    @patch("app.services.message_service.filter_message")
    def test_lookup_not_called_when_filter_rejects(self, mock_filter, mock_lookup, mock_db):
        from app.services.message_service import process_slack_message

        mock_filter.return_value = False

        payload = {
            "type": "event_callback",
            "team_id": "T123",
            "event": {"type": "message", "user": "U123", "text": "lunch?", "ts": "1", "channel": "C1"},
        }

        result = process_slack_message(payload, "1")

        assert result is False
        mock_lookup.assert_not_called()
        mock_db.upsert_slack_user.assert_not_called()
