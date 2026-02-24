"""Test gRPC server functionality."""
import grpc
import sys
import os

# Add generated proto files to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated'))

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc


def test_classify_message():
    """Test ClassifyMessage RPC call."""
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = filter_pb2_grpc.FilterServiceStub(channel)
        
        request = filter_pb2.ClassifyRequest(
            message="This is a test message for classification"
        )
        
        response = stub.ClassifyMessage(request)
        
        assert response.category is not None
        assert response.severity is not None
        assert isinstance(response.is_risk, bool)
        assert 0 <= response.category_confidence <= 1.0
        assert 0 <= response.severity_confidence <= 1.0
        
        print(f"✓ Category: {response.category} ({response.category_confidence:.2f})")
        print(f"✓ Severity: {response.severity} ({response.severity_confidence:.2f})")
        print(f"✓ Is Risk: {response.is_risk}")


if __name__ == '__main__':
    test_classify_message()
