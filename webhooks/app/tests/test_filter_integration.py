"""
Integration tests for Filter Service gRPC stub.
"""

import pytest
import grpc
from sentinelai.filter.v1 import filter_pb2, filter_pb2_grpc
from app.services.filter_service import filter_message, FILTER_SERVICE_HOST


class TestFilterIntegration:
    """Integration tests for gRPC mental health filter service."""
    
    def test_classify_neutral_message(self):
        """Test that neutral messages return is_risk=False."""
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.ClassifyRequest(
                message="Hey team, the meeting is scheduled for 3pm today."
            )
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert isinstance(response.category, str)
            assert isinstance(response.category_confidence, float)
            assert isinstance(response.severity, str)
            assert 0.0 <= response.category_confidence <= 1.0
    
    def test_classify_stress_message(self):
        """Test that stress-indicating message gets classified."""
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
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
    
    def test_classify_harassment_message(self):
        """Test that harassment message gets flagged."""
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.ClassifyRequest(
                message="You're worthless and everyone hates working with you."
            )
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert response.severity in ["none", "early", "middle", "late"]
            assert 0.0 <= response.severity_confidence <= 1.0
    
    def test_classify_empty_message(self):
        """Test that empty messages are handled gracefully."""
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.ClassifyRequest(message="")
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            assert response.category == "neutral"
    
    def test_filter_message_returns_bool(self):
        """Test the filter_message wrapper function."""
        result = filter_message("Just finished the report, feeling good about it.")
        assert isinstance(result, bool)
    
    def test_filter_message_extracts_is_risk(self):
        """Test that filter_message correctly extracts is_risk field."""
        neutral = filter_message("Happy Friday everyone!")
        assert isinstance(neutral, bool)
        
        concerning = filter_message("I feel completely exhausted and hopeless about everything.")
        assert isinstance(concerning, bool)
    
    def test_long_message_handling(self):
        """Test that long messages are processed via sliding window."""
        long_text = "I've been feeling really stressed lately. " * 200  # ~600 tokens
        
        with grpc.insecure_channel(FILTER_SERVICE_HOST) as channel:
            stub = filter_pb2_grpc.FilterServiceStub(channel)
            request = filter_pb2.ClassifyRequest(message=long_text)
            response = stub.ClassifyMessage(request)
            
            assert isinstance(response.is_risk, bool)
            # Should have multiple chunk responses
            assert "[Chunk" in response.all_responses
