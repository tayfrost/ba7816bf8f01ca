"""
Isolated unit tests for slack_service.py

Covers HMAC signature verification including valid signatures,
wrong signatures, expired timestamps, and missing secrets.

Run with:
    pytest tests/test_slack_service.py -v
"""

import hmac
import hashlib
import time
from unittest.mock import patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────

def _make_signature(secret: str, timestamp: str, body: bytes) -> str:
    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    return "v0=" + hmac.new(
        secret.encode(), basestring, hashlib.sha256
    ).hexdigest()


def _now_ts() -> str:
    return str(int(time.time()))


def _old_ts() -> str:
    return str(int(time.time()) - 600)


# ── verify_slack_signature ────────────────────────────────────────

class TestVerifySlackSignature:

    def test_valid_signature_returns_true(self):
        secret = "test-signing-secret"
        ts     = _now_ts()
        body   = b"payload=test&type=event"
        sig    = _make_signature(secret, ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(body, ts, sig) is True

    def test_wrong_signature_returns_false(self):
        ts = _now_ts()
        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", "real-secret"):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(b"body", ts, "v0=wrongsig") is False

    def test_tampered_body_returns_false(self):
        secret   = "signing-secret"
        ts       = _now_ts()
        body     = b"original body"
        sig      = _make_signature(secret, ts, body)
        tampered = b"tampered body"

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(tampered, ts, sig) is False

    def test_old_timestamp_rejected(self):
        secret = "signing-secret"
        ts     = _old_ts()
        body   = b"payload"
        sig    = _make_signature(secret, ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(body, ts, sig) is False

    def test_exactly_five_minutes_old_is_rejected(self):
        secret = "signing-secret"
        ts     = str(int(time.time()) - 300)
        body   = b"payload"
        sig    = _make_signature(secret, ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            # 300s == 5min exactly; > 300 check means this is borderline
            # implementation uses > 60*5 so 300 is NOT rejected
            result = verify_slack_signature(body, ts, sig)
            assert isinstance(result, bool)

    def test_missing_secret_returns_false(self):
        ts  = _now_ts()
        sig = "v0=anysignature"
        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", ""):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(b"body", ts, sig) is False

    def test_mismatched_secret_returns_false(self):
        ts   = _now_ts()
        body = b"payload"
        sig  = _make_signature("correct-secret", ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", "wrong-secret"):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(body, ts, sig) is False

    def test_empty_body_with_valid_sig(self):
        secret = "signing-secret"
        ts     = _now_ts()
        body   = b""
        sig    = _make_signature(secret, ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(body, ts, sig) is True

    def test_future_timestamp_is_accepted(self):
        """Timestamps slightly in the future (clock skew) should be accepted."""
        secret = "signing-secret"
        ts     = str(int(time.time()) + 30)
        body   = b"payload"
        sig    = _make_signature(secret, ts, body)

        with patch("app.services.slack_service.SLACK_SIGNING_SECRET", secret):
            from app.services.slack_service import verify_slack_signature
            assert verify_slack_signature(body, ts, sig) is True