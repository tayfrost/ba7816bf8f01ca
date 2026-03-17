"""Test gRPC server functionality."""

import grpc
import sys
from pathlib import Path

# Add generated proto files to path
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))

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
        assert response.all_responses is not None

        print(f"✓ Category: {response.category} ({response.category_confidence:.2f})")
        print(f"✓ Severity: {response.severity} ({response.severity_confidence:.2f})")
        print(f"✓ Is Risk: {response.is_risk}")
        print(f"✓ All Responses: {response.all_responses}")


if __name__ == '__main__':
    test_classify_message()
