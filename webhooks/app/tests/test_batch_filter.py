"""
Tests for filter_messages() batch client and fallback behaviour.
Unit tests with mocks — no server needed.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List
import grpc


def _mock_classify_response(is_risk, category="neutral", cat_conf=0.9,
                             severity="none", sev_conf=0.9):
    resp = MagicMock()
    resp.is_risk = is_risk
    resp.category = category
    resp.category_confidence = cat_conf
    resp.severity = severity
    resp.severity_confidence = sev_conf
    resp.all_responses = f"[Chunk 1] category={category}"
    return resp


def _mock_batch_response(flags):
    resp = MagicMock()
    resp.results = [
        _mock_classify_response(f, "stress" if f else "neutral") for f in flags
    ]
    return resp


class TestFilterMessagesBatch:

    @patch("app.services.filter_service.filter_pb2_grpc.FilterServiceStub")
    @patch("app.services.filter_service.grpc.insecure_channel")
    def test_returns_correct_length(self, mock_ch, mock_stub_cls):
        from app.services.filter_service import filter_messages
        stub = MagicMock()
        stub.ClassifyMessages.return_value = _mock_batch_response([False, True, False])
        mock_stub_cls.return_value = stub
        mock_ch.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ch.return_value.__exit__ = MagicMock(return_value=False)

        assert filter_messages(["a", "b", "c"]) == [False, True, False]

    @patch("app.services.filter_service.filter_pb2_grpc.FilterServiceStub")
    @patch("app.services.filter_service.grpc.insecure_channel")
    def test_preserves_order(self, mock_ch, mock_stub_cls):
        from app.services.filter_service import filter_messages
        flags = [False, True, False, True]
        stub = MagicMock()
        stub.ClassifyMessages.return_value = _mock_batch_response(flags)
        mock_stub_cls.return_value = stub
        mock_ch.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ch.return_value.__exit__ = MagicMock(return_value=False)

        assert filter_messages(["a", "b", "c", "d"]) == flags

    def test_empty_list(self):
        from app.services.filter_service import filter_messages
        assert filter_messages([]) == []

    @patch("app.services.filter_service.filter_message")
    def test_single_message_delegates_to_single_rpc(self, mock_single):
        from app.services.filter_service import filter_messages
        mock_single.return_value = True
        assert filter_messages(["one"]) == [True]
        mock_single.assert_called_once_with("one")

    @patch("app.services.filter_service.filter_message")
    @patch("app.services.filter_service.filter_pb2_grpc.FilterServiceStub")
    @patch("app.services.filter_service.grpc.insecure_channel")
    def test_fallback_on_grpc_error(self, mock_ch, mock_stub_cls, mock_single):
        from app.services.filter_service import filter_messages
        stub = MagicMock()
        stub.ClassifyMessages.side_effect = grpc.RpcError()
        mock_stub_cls.return_value = stub
        mock_ch.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ch.return_value.__exit__ = MagicMock(return_value=False)
        mock_single.side_effect = [False, True, False]

        assert filter_messages(["a", "b", "c"]) == [False, True, False]
        assert mock_single.call_count == 3

    @patch("app.services.filter_service.filter_message")
    @patch("app.services.filter_service.filter_pb2_grpc.FilterServiceStub")
    @patch("app.services.filter_service.grpc.insecure_channel")
    def test_fallback_on_unexpected_error(self, mock_ch, mock_stub_cls, mock_single):
        from app.services.filter_service import filter_messages
        stub = MagicMock()
        stub.ClassifyMessages.side_effect = RuntimeError("oops")
        mock_stub_cls.return_value = stub
        mock_ch.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ch.return_value.__exit__ = MagicMock(return_value=False)
        mock_single.side_effect = [True, True]

        assert filter_messages(["a", "b"]) == [True, True]


class TestBatchFilterIntegration:
    """Requires filter gRPC server on localhost:50051. Run with: pytest -m integration"""

    @pytest.mark.integration
    def test_batch_via_grpc(self):
        from app.services.filter_service import filter_messages
        results = filter_messages([
            "Happy Friday!",
            "I'm struggling with severe anxiety",
            "Lunch at noon?",
        ])
        assert len(results) == 3
        assert all(isinstance(r, bool) for r in results)
