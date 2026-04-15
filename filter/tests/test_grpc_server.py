"""Test gRPC server functionality."""

import grpc
import pytest
import sys
from pathlib import Path

# Add generated proto files to path
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))

from filter.v1 import filter_pb2
from filter.v1 import filter_pb2_grpc


def _wait_for_server_or_skip(channel: grpc.Channel) -> None:
    try:
        grpc.channel_ready_future(channel).result(timeout=1.5)
    except grpc.FutureTimeoutError:
        pytest.skip("Filter gRPC server not available on localhost:50051")


def test_classify_message():
    """Test ClassifyMessage RPC call."""
    with grpc.insecure_channel('localhost:50051') as channel:
        _wait_for_server_or_skip(channel)
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


def test_classify_message_empty_input():
    """Empty message should be handled safely without server errors."""
    with grpc.insecure_channel('localhost:50051') as channel:
        _wait_for_server_or_skip(channel)
        stub = filter_pb2_grpc.FilterServiceStub(channel)

        response = stub.ClassifyMessage(filter_pb2.ClassifyRequest(message=""))

        assert response.category is not None
        assert response.severity is not None
        assert isinstance(response.is_risk, bool)
        assert 0 <= response.category_confidence <= 1.0
        assert 0 <= response.severity_confidence <= 1.0


def test_classify_message_long_input_sliding_window():
    """Very long message should classify successfully and include chunk traces."""
    long_message = " ".join([
        "I've been feeling really stressed out lately.",
        "Work has been overwhelming and deadlines keep piling up.",
        "I can't seem to catch a break and my sleep is suffering.",
        "Every day feels like a struggle and I'm exhausted all the time.",
        "I don't know how much longer I can keep this pace up.",
    ] * 10)

    with grpc.insecure_channel('localhost:50051') as channel:
        _wait_for_server_or_skip(channel)
        stub = filter_pb2_grpc.FilterServiceStub(channel)

        response = stub.ClassifyMessage(filter_pb2.ClassifyRequest(message=long_message))

        assert response.category is not None
        assert response.severity is not None
        assert isinstance(response.is_risk, bool)
        assert 0 <= response.category_confidence <= 1.0
        assert 0 <= response.severity_confidence <= 1.0
        assert response.all_responses is not None
        assert "[Chunk" in response.all_responses


if __name__ == '__main__':
    test_classify_message()
