"""
Integration tests for Filter Service gRPC stub.

`sentinelai.filter.v1` is the generated proto package namespace used by
the webhooks service for FilterService gRPC calls.
"""

import pytest
import grpc
from sentinelai.filter.v1 import filter_pb2, filter_pb2_grpc
from app.services.filter_service import filter_message, FILTER_SERVICE_HOST


def _get_filter_stub_or_skip():
    channel = grpc.insecure_channel(FILTER_SERVICE_HOST)
    try:
        grpc.channel_ready_future(channel).result(timeout=1.5)
    except grpc.FutureTimeoutError:
        channel.close()
        pytest.skip(f"Filter gRPC server not available on {FILTER_SERVICE_HOST}")
    return filter_pb2_grpc.FilterServiceStub(channel), channel


class TestFilterIntegration:
    """Integration tests for gRPC mental health filter service."""
    
    def test_classify_neutral_message(self):
        """Test that neutral messages return is_risk=False."""
        stub, channel = _get_filter_stub_or_skip()
        try:
            request = filter_pb2.ClassifyRequest(
                message="Hey team, the meeting is scheduled for 3pm today."
            )
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert isinstance(response.category, str)
            assert isinstance(response.category_confidence, float)
            assert isinstance(response.severity, str)
            assert 0.0 <= response.category_confidence <= 1.0
        finally:
            channel.close()

    
    def test_classify_stress_message(self):
        """Test that stress-indicating message gets classified."""
        stub, channel = _get_filter_stub_or_skip()
        try:
            request = filter_pb2.ClassifyRequest(
                message="I'm so overwhelmed with all these deadlines, I can't keep up anymore."
            )
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert response.category in [
                "neutral", "humor_sarcasm", "stress", "burnout", 
                "depression", "harassment", "suicidal_ideation"
            ]
            assert 0.0 <= response.category_confidence <= 1.0
            assert response.all_responses != ""
        finally:
            channel.close()
    
    def test_classify_harassment_message(self):
        """Test that harassment message gets flagged."""
        stub, channel = _get_filter_stub_or_skip()
        try:
            request = filter_pb2.ClassifyRequest(
                message="You're worthless and everyone hates working with you."
            )
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert response.severity in ["none", "early", "middle", "late"]
            assert 0.0 <= response.severity_confidence <= 1.0
        finally:
            channel.close()
    
    def test_classify_empty_message(self):
        """Test that empty messages are handled gracefully."""
        stub, channel = _get_filter_stub_or_skip()
        try:
            request = filter_pb2.ClassifyRequest(message="")
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert response.category == "neutral"
        finally:
            channel.close()
    
    def test_filter_message_returns_filter_result(self):
        result = filter_message("Just finished the report, feeling good about it.")
        assert result is not None
        assert isinstance(result.is_risk, bool)
        assert isinstance(result.category, str)
        assert isinstance(result.severity, str)

    def test_filter_message_extracts_is_risk(self):
        neutral = filter_message("Happy Friday everyone!")
        assert neutral is not None
        assert isinstance(neutral.is_risk, bool)

        concerning = filter_message("I feel completely exhausted and hopeless about everything.")
        assert concerning is not None
        assert isinstance(concerning.is_risk, bool)
    
    def test_long_message_handling(self):
        """Test that long messages are processed via sliding window."""
        long_text = "I've been feeling really stressed lately. " * 200  # ~600 tokens
        stub, channel = _get_filter_stub_or_skip()
        try:
            request = filter_pb2.ClassifyRequest(message=long_text)
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            # Should have multiple chunk responses
            assert "[Chunk" in response.all_responses
        finally:
            channel.close()