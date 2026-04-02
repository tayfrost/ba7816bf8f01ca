"""
Isolated unit tests for gmail_service.py

Covers OIDC Bearer token verification including valid tokens,
missing headers, wrong issuers, and invalid JWTs.

Run with:
    pytest tests/test_gmail_service.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from starlette.testclient import TestClient
from starlette.requests import Request
from starlette.datastructures import Headers


# ── Helpers ───────────────────────────────────────────────────────

def _make_request(auth_header=None):
    """Build a minimal Starlette Request with optional Authorization header."""
    headers = {}
    if auth_header:
        headers["authorization"] = auth_header
    scope = {
        "type":    "http",
        "method":  "POST",
        "path":    "/gmail/events",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in headers.items()
        ],
        "query_string": b"",
    }
    return Request(scope)


# ── verify_gmail_token ────────────────────────────────────────────

class TestVerifyGmailToken:

    def test_raises_401_when_no_auth_header(self):
        request = _make_request()
        from app.services.gmail_service import verify_gmail_token
        with pytest.raises(HTTPException) as exc_info:
            verify_gmail_token(request)
        assert exc_info.value.status_code == 401
        assert "Missing Bearer token" in exc_info.value.detail

    def test_raises_401_when_not_bearer(self):
        request = _make_request(auth_header="Basic abc123")
        from app.services.gmail_service import verify_gmail_token
        with pytest.raises(HTTPException) as exc_info:
            verify_gmail_token(request)
        assert exc_info.value.status_code == 401

    def test_raises_401_on_invalid_jwt(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.gmail_service.google_id_token.verify_oauth2_token",
            lambda token, req, audience: (_ for _ in ()).throw(
                ValueError("bad token")
            ),
        )
        request = _make_request(auth_header="Bearer badtoken")
        from app.services.gmail_service import verify_gmail_token
        with pytest.raises(HTTPException) as exc_info:
            verify_gmail_token(request)
        assert exc_info.value.status_code == 401
        assert "Invalid JWT" in exc_info.value.detail

    def test_raises_401_on_wrong_issuer(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.gmail_service.google_id_token.verify_oauth2_token",
            lambda token, req, audience: {"iss": "https://evil.com", "email": "x"},
        )
        request = _make_request(auth_header="Bearer validtoken")
        from app.services.gmail_service import verify_gmail_token
        with pytest.raises(HTTPException) as exc_info:
            verify_gmail_token(request)
        assert exc_info.value.status_code == 401
        assert "issuer" in exc_info.value.detail.lower()

    def test_accepts_accounts_google_com_issuer(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.gmail_service.google_id_token.verify_oauth2_token",
            lambda token, req, audience: {
                "iss": "https://accounts.google.com", "email": "x"
            },
        )
        request = _make_request(auth_header="Bearer validtoken")
        from app.services.gmail_service import verify_gmail_token
        # Should not raise
        verify_gmail_token(request)

    def test_accepts_accounts_google_com_without_https(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.gmail_service.google_id_token.verify_oauth2_token",
            lambda token, req, audience: {
                "iss": "accounts.google.com", "email": "x"
            },
        )
        request = _make_request(auth_header="Bearer validtoken")
        from app.services.gmail_service import verify_gmail_token
        verify_gmail_token(request)

    def test_strips_whitespace_from_token(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "app.services.gmail_service.google_id_token.verify_oauth2_token",
            lambda token, req, audience: (
                captured.update(token=token) or
                {"iss": "https://accounts.google.com"}
            ),
        )
        request = _make_request(auth_header="Bearer   mytoken  ")
        from app.services.gmail_service import verify_gmail_token
        verify_gmail_token(request)
        assert captured["token"] == "mytoken"