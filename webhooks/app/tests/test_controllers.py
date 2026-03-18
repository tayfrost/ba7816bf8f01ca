"""
Isolated unit tests for slack_controller.py and gmail_controller.py

Uses FastAPI TestClient to exercise HTTP concerns: routing, status codes,
request validation, company_id injection, signature gating, and challenge
handshake. All service layer calls are monkeypatched.

Run with:
    pytest tests/test_controllers.py -v
"""

import hmac
import hashlib
import json
import time
import base64
import uuid
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── App fixtures ──────────────────────────────────────────────────

@pytest.fixture()
def slack_client(monkeypatch):
    """TestClient with only the Slack router mounted."""
    monkeypatch.setenv("SLACK_CLIENT_ID",     "cid")
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SLACK_REDIRECT_URI",  "https://example.com/callback")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "signing-secret")

    from app.controllers.slack_controller import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture()
def gmail_client(monkeypatch):
    """TestClient with only the Gmail router mounted."""
    monkeypatch.setenv("GMAIL_CLIENT_ID",     "gcid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "gcsecret")
    monkeypatch.setenv("BASE_URL",            "https://example.com")
    monkeypatch.setenv("GMAIL_WEBHOOK_ENDPOINT", "https://example.com/gmail/events")

    from app.controllers.gmail_controller import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)



# ── Slack signature helper ────────────────────────────────────────

def _slack_sig(body: bytes, ts: str, secret: str = "signing-secret") -> str:
    base = f"v0:{ts}:{body.decode()}".encode()
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def _slack_headers(body: bytes, secret: str = "signing-secret") -> dict:
    ts  = str(int(time.time()))
    sig = _slack_sig(body, ts, secret)
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature":         sig,
        "Content-Type":              "application/json",
    }


def _event_payload(team_id="T123", user="U999", text="hello", channel="C1"):
    return json.dumps({
        "type":    "event_callback",
        "team_id": team_id,
        "event":   {
            "type":    "message",
            "user":    user,
            "text":    text,
            "ts":      "1700000000.000",
            "channel": channel,
        },
    }).encode()


# ═══════════════════════════════════════════════════════════════════
# Slack controller
# ═══════════════════════════════════════════════════════════════════

class TestSlackOauthCallback:

    def test_missing_code_returns_400(self, slack_client):
        resp = slack_client.get("/slack/oauth/callback?state=1")
        assert resp.status_code == 400
        assert "Missing code" in resp.json()["detail"]

    def test_missing_state_returns_400(self, slack_client, monkeypatch):
        resp = slack_client.get("/slack/oauth/callback?code=abc")
        assert resp.status_code == 400
        assert "company_id" in resp.json()["detail"].lower()
        
    def test_invalid_state_returns_400(self, slack_client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        monkeypatch.setattr(
            "app.controllers.slack_controller.httpx.AsyncClient",
            lambda: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
                post=AsyncMock(return_value=mock_resp)
            )), __aexit__=AsyncMock(return_value=False)),
        )
        resp = slack_client.get("/slack/oauth/callback?code=abc&state=notanint")
        assert resp.status_code == 400
        assert "Invalid company_id" in resp.json()["detail"]

    def test_company_id_injected_into_oauth_data(self, slack_client, monkeypatch):
        captured  = {}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True, "team": {"id": "T123"}, "access_token": "xoxb-x"
        }
        monkeypatch.setattr(
            "app.controllers.slack_controller.httpx.AsyncClient",
            lambda: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
                post=AsyncMock(return_value=mock_resp)
            )), __aexit__=AsyncMock(return_value=False)),
        )
        monkeypatch.setattr(
            "app.controllers.slack_controller.process_slack_oauth",
            lambda data: captured.update(data) or SimpleNamespace(
                team_id="T123", access_token="x"
            ),
        )
        slack_client.get("/slack/oauth/callback?code=abc&state=42")
        assert captured.get("_company_id") == 42

    def test_successful_oauth_returns_ok(self, slack_client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True, "team": {"id": "T123"}, "access_token": "xoxb-x"
        }
        monkeypatch.setattr(
            "app.controllers.slack_controller.httpx.AsyncClient",
            lambda: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
                post=AsyncMock(return_value=mock_resp)
            )), __aexit__=AsyncMock(return_value=False)),
        )
        monkeypatch.setattr(
            "app.controllers.slack_controller.process_slack_oauth",
            lambda data: SimpleNamespace(team_id="T123", access_token="x"),
        )
        resp = slack_client.get("/slack/oauth/callback?code=abc&state=1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_process_oauth_value_error_returns_400(self, slack_client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "bad_request"}
        monkeypatch.setattr(
            "app.controllers.slack_controller.httpx.AsyncClient",
            lambda: AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
                post=AsyncMock(return_value=mock_resp)
            )), __aexit__=AsyncMock(return_value=False)),
        )
        monkeypatch.setattr(
            "app.controllers.slack_controller.process_slack_oauth",
            lambda data: (_ for _ in ()).throw(ValueError("bad_request")),
        )
        resp = slack_client.get("/slack/oauth/callback?code=abc&state=1")
        assert resp.status_code == 400


class TestSlackEvents:

    def test_url_verification_challenge_returned(self, slack_client):
        payload = json.dumps({
            "type":      "url_verification",
            "challenge": "test_challenge_abc",
        }).encode()
        resp = slack_client.post(
            "/slack/events",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "test_challenge_abc"

    def test_invalid_signature_returns_403(self, slack_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.slack_controller.verify_slack_signature",
            lambda body, ts, sig: False,
        )
        body = _event_payload()
        resp = slack_client.post(
            "/slack/events",
            content=body,
            headers={"Content-Type": "application/json",
                     "X-Slack-Request-Timestamp": "123",
                     "X-Slack-Signature": "v0=bad"},
        )
        assert resp.status_code == 403

    def test_valid_event_returns_ok(self, slack_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.slack_controller.verify_slack_signature",
            lambda body, ts, sig: True,
        )
        monkeypatch.setattr(
            "app.controllers.slack_controller.process_slack_message",
            lambda payload, ts: True,
        )
        body = _event_payload()
        resp = slack_client.post(
            "/slack/events",
            content=body,
            headers={"Content-Type": "application/json",
                     "X-Slack-Request-Timestamp": str(int(time.time())),
                     "X-Slack-Signature": "v0=placeholder"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_process_message_called_with_payload(self, slack_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.slack_controller.verify_slack_signature",
            lambda body, ts, sig: True,
        )
        captured = {}
        monkeypatch.setattr(
            "app.controllers.slack_controller.process_slack_message",
            lambda payload, ts: captured.update(payload=payload),
        )
        body    = _event_payload(team_id="T999")
        resp    = slack_client.post(
            "/slack/events",
            content=body,
            headers={"Content-Type": "application/json",
                     "X-Slack-Request-Timestamp": str(int(time.time())),
                     "X-Slack-Signature": "v0=placeholder"},
        )
        assert resp.status_code == 200
        assert captured["payload"]["team_id"] == "T999"


# ═══════════════════════════════════════════════════════════════════
# Gmail controller
# ═══════════════════════════════════════════════════════════════════

class TestGmailOauthLogin:

    def test_missing_company_id_returns_400(self, gmail_client):
        resp = gmail_client.get("/gmail/oauth/login",
                                follow_redirects=False)
        assert resp.status_code == 422  # FastAPI missing required param

    def test_redirects_to_google_consent_url(self, gmail_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.gmail_controller.get_gmail_auth_url",
            lambda cid: "https://accounts.google.com/o/oauth2/auth?state=1",
        )
        resp = gmail_client.get("/gmail/oauth/login?company_id=1",
                                follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers["location"]


class TestGmailOauthCallback:

    def test_missing_code_returns_400(self, gmail_client):
        resp = gmail_client.get("/gmail/oauth/callback?state=1")
        assert resp.status_code == 400
        assert "Missing code" in resp.json()["detail"]

    def test_missing_state_returns_400(self, gmail_client):
        resp = gmail_client.get("/gmail/oauth/callback?code=abc")
        assert resp.status_code == 400
        assert "company_id" in resp.json()["detail"].lower()

    def test_invalid_state_returns_400(self, gmail_client):
        resp = gmail_client.get("/gmail/oauth/callback?code=abc&state=notanint")
        assert resp.status_code == 400
        assert "Invalid company_id" in resp.json()["detail"]

    def test_successful_callback_returns_ok(self, gmail_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.gmail_controller.process_gmail_oauth",
            lambda code, company_id: "emp@example.com",
        )
        resp = gmail_client.get("/gmail/oauth/callback?code=abc&state=1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["connected_user"] == "emp@example.com"

    def test_runtime_error_returns_500(self, gmail_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.gmail_controller.process_gmail_oauth",
            lambda code, company_id: (_ for _ in ()).throw(
                RuntimeError("DB error")
            ),
        )
        resp = gmail_client.get("/gmail/oauth/callback?code=abc&state=1")
        assert resp.status_code == 500


class TestGmailEvents:

    def test_invalid_oidc_token_returns_401(self, gmail_client, monkeypatch):
        from fastapi import HTTPException
        monkeypatch.setattr(
            "app.controllers.gmail_controller.verify_gmail_token",
            lambda req: (_ for _ in ()).throw(
                HTTPException(status_code=401, detail="Missing Bearer token")
            ),
        )
        resp = gmail_client.post(
            "/gmail/events",
            json={"message": {"data": "dGVzdA=="}},
        )
        assert resp.status_code == 401

    def test_valid_event_returns_ok(self, gmail_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.gmail_controller.verify_gmail_token",
            lambda req: None,
        )
        monkeypatch.setattr(
            "app.controllers.gmail_controller.process_gmail_event",
            lambda payload: True,
        )
        resp = gmail_client.post(
            "/gmail/events",
            json={"message": {"data": "dGVzdA=="}},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_stored_field_reflects_processing_result(self, gmail_client, monkeypatch):
        monkeypatch.setattr(
            "app.controllers.gmail_controller.verify_gmail_token",
            lambda req: None,
        )
        monkeypatch.setattr(
            "app.controllers.gmail_controller.process_gmail_event",
            lambda payload: False,
        )
        resp = gmail_client.post(
            "/gmail/events",
            json={"message": {"data": "dGVzdA=="}},
        )
        assert resp.json()["stored"] is False

    def test_verify_token_called_before_processing(self, gmail_client, monkeypatch):
        call_order = []
        monkeypatch.setattr(
            "app.controllers.gmail_controller.verify_gmail_token",
            lambda req: call_order.append("verify"),
        )
        monkeypatch.setattr(
            "app.controllers.gmail_controller.process_gmail_event",
            lambda payload: call_order.append("process") or True,
        )
        gmail_client.post(
            "/gmail/events",
            json={"message": {"data": "dGVzdA=="}},
        )
        assert call_order == ["verify", "process"]