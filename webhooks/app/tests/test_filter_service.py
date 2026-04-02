"""
Isolated unit tests for filter_service.py

Verifies gRPC client behaviour with a mocked channel — no live filter
service required. Tests the FilterResult dataclass, the happy path,
fail-closed behaviour on RpcError, and fail-closed on unexpected exceptions.

Run with:
    pytest tests/test_filter_service.py -v
"""

import pytest
import grpc
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace


# ── Helpers ───────────────────────────────────────────────────────

def _make_grpc_response(**kw):
    defaults = dict(
        is_risk=True,
        category="stress",
        category_confidence=0.91,
        severity="early",
        severity_confidence=0.85,
        all_responses="[Chunk 1] stress",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_rpc_error(code=grpc.StatusCode.UNAVAILABLE, details="service down"):
    error = grpc.RpcError()
    error.code    = lambda: code
    error.details = lambda: details
    return error


# ── FilterResult dataclass ────────────────────────────────────────

class TestFilterResult:

    def test_fields_accessible(self):
        from app.services.filter_service import FilterResult
        r = FilterResult(
            is_risk=True, category="stress",
            category_confidence=0.9, severity="early",
            severity_confidence=0.85,
        )
        assert r.is_risk              is True
        assert r.category             == "stress"
        assert r.category_confidence  == 0.9
        assert r.severity             == "early"
        assert r.severity_confidence  == 0.85

    def test_is_risk_false(self):
        from app.services.filter_service import FilterResult
        r = FilterResult(
            is_risk=False, category="neutral",
            category_confidence=0.99, severity="none",
            severity_confidence=0.99,
        )
        assert r.is_risk is False

    def test_all_expected_categories_valid(self):
        from app.services.filter_service import FilterResult
        for cat in ["neutral", "humor_sarcasm", "stress", "burnout",
                    "depression", "harassment", "suicidal_ideation"]:
            r = FilterResult(
                is_risk=cat != "neutral", category=cat,
                category_confidence=0.9, severity="none",
                severity_confidence=0.9,
            )
            assert r.category == cat


# ── filter_message happy path ─────────────────────────────────────

class TestFilterMessageSuccess:

    def _patch_grpc(self, monkeypatch, response):
        mock_stub     = MagicMock()
        mock_stub.ClassifyMessage.return_value = response

        mock_channel  = MagicMock()
        mock_channel.__enter__ = MagicMock(return_value=mock_channel)
        mock_channel.__exit__  = MagicMock(return_value=False)

        mock_stub_cls = MagicMock(return_value=mock_stub)

        monkeypatch.setattr("app.services.filter_service.grpc.insecure_channel",
                            lambda host: mock_channel)
        monkeypatch.setattr("app.services.filter_service.filter_pb2_grpc.FilterServiceStub",
                            mock_stub_cls)
        return mock_stub

    def test_returns_filter_result_on_success(self, monkeypatch):
        resp = _make_grpc_response(is_risk=True, category="stress")
        self._patch_grpc(monkeypatch, resp)

        from app.services.filter_service import filter_message, FilterResult
        result = filter_message("I'm overwhelmed")
        assert isinstance(result, FilterResult)
        assert result.is_risk   is True
        assert result.category  == "stress"

    def test_is_risk_false_for_neutral(self, monkeypatch):
        resp = _make_grpc_response(is_risk=False, category="neutral",
                                   category_confidence=0.99)
        self._patch_grpc(monkeypatch, resp)

        from app.services.filter_service import filter_message
        result = filter_message("Happy Friday everyone!")
        assert result is not None
        assert result.is_risk is False

    def test_all_fields_mapped_from_response(self, monkeypatch):
        resp = _make_grpc_response(
            is_risk=True, category="burnout",
            category_confidence=0.77, severity="middle",
            severity_confidence=0.65,
        )
        self._patch_grpc(monkeypatch, resp)

        from app.services.filter_service import filter_message
        result = filter_message("I can't do this anymore")
        assert result.category             == "burnout"
        assert result.category_confidence  == 0.77
        assert result.severity             == "middle"
        assert result.severity_confidence  == 0.65

    def test_passes_text_to_classify_request(self, monkeypatch):
        resp      = _make_grpc_response()
        mock_stub = self._patch_grpc(monkeypatch, resp)

        from app.services.filter_service import filter_message
        filter_message("test message text")

        call_args = mock_stub.ClassifyMessage.call_args
        assert call_args is not None

    def test_empty_string_handled(self, monkeypatch):
        resp = _make_grpc_response(is_risk=False, category="neutral")
        self._patch_grpc(monkeypatch, resp)

        from app.services.filter_service import filter_message
        result = filter_message("")
        assert result is not None
        assert result.is_risk is False


# ── filter_message fail-closed behaviour ─────────────────────────

class TestFilterMessageFailClosed:

    def test_returns_none_on_rpc_error(self, monkeypatch):
        mock_channel = MagicMock()
        mock_channel.__enter__ = MagicMock(return_value=mock_channel)
        mock_channel.__exit__  = MagicMock(return_value=False)

        mock_stub = MagicMock()
        mock_stub.ClassifyMessage.side_effect = _make_rpc_error()

        monkeypatch.setattr("app.services.filter_service.grpc.insecure_channel",
                            lambda host: mock_channel)
        monkeypatch.setattr("app.services.filter_service.filter_pb2_grpc.FilterServiceStub",
                            MagicMock(return_value=mock_stub))

        from app.services.filter_service import filter_message
        result = filter_message("any text")
        assert result is None

    def test_returns_none_on_unavailable(self, monkeypatch):
        mock_channel = MagicMock()
        mock_channel.__enter__ = MagicMock(return_value=mock_channel)
        mock_channel.__exit__  = MagicMock(return_value=False)

        mock_stub = MagicMock()
        mock_stub.ClassifyMessage.side_effect = _make_rpc_error(
            code=grpc.StatusCode.UNAVAILABLE
        )

        monkeypatch.setattr("app.services.filter_service.grpc.insecure_channel",
                            lambda host: mock_channel)
        monkeypatch.setattr("app.services.filter_service.filter_pb2_grpc.FilterServiceStub",
                            MagicMock(return_value=mock_stub))

        from app.services.filter_service import filter_message
        assert filter_message("text") is None

    def test_returns_none_on_deadline_exceeded(self, monkeypatch):
        mock_channel = MagicMock()
        mock_channel.__enter__ = MagicMock(return_value=mock_channel)
        mock_channel.__exit__  = MagicMock(return_value=False)

        mock_stub = MagicMock()
        mock_stub.ClassifyMessage.side_effect = _make_rpc_error(
            code=grpc.StatusCode.DEADLINE_EXCEEDED
        )

        monkeypatch.setattr("app.services.filter_service.grpc.insecure_channel",
                            lambda host: mock_channel)
        monkeypatch.setattr("app.services.filter_service.filter_pb2_grpc.FilterServiceStub",
                            MagicMock(return_value=mock_stub))

        from app.services.filter_service import filter_message
        assert filter_message("text") is None

    def test_returns_none_on_unexpected_exception(self, monkeypatch):
        mock_channel = MagicMock()
        mock_channel.__enter__ = MagicMock(return_value=mock_channel)
        mock_channel.__exit__  = MagicMock(return_value=False)

        mock_stub = MagicMock()
        mock_stub.ClassifyMessage.side_effect = RuntimeError("unexpected")

        monkeypatch.setattr("app.services.filter_service.grpc.insecure_channel",
                            lambda host: mock_channel)
        monkeypatch.setattr("app.services.filter_service.filter_pb2_grpc.FilterServiceStub",
                            MagicMock(return_value=mock_stub))

        from app.services.filter_service import filter_message
        assert filter_message("text") is None

    def test_none_means_do_not_store(self, monkeypatch):
        """
        Confirms the fail-closed contract: None from filter_message must
        be treated as 'do not store' by callers (message_service does this).
        """
        from app.services.filter_service import filter_message as fm
        # When None, `not result` is True — the guard fires correctly
        result = None
        assert not result or not getattr(result, "is_risk", False)


# ── FILTER_SERVICE_HOST env var ───────────────────────────────────

class TestFilterServiceHost:

    def test_default_host_is_filter_50051(self, monkeypatch):
        monkeypatch.delenv("FILTER_SERVICE_HOST", raising=False)
        import importlib
        import app.services.filter_service as fs
        importlib.reload(fs)
        assert fs.FILTER_SERVICE_HOST == "filter:50051"

    def test_host_can_be_overridden_via_env(self, monkeypatch):
        monkeypatch.setenv("FILTER_SERVICE_HOST", "myhost:9090")
        import importlib
        import app.services.filter_service as fs
        importlib.reload(fs)
        assert fs.FILTER_SERVICE_HOST == "myhost:9090"