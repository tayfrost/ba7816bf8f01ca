"""
Batch classification tests for ClassifyMessages RPC.

Follows the same pattern as test_grpc_server.py:
  - Connects to localhost:50051 (server must be running)
  - Uses filter.v1 proto stubs
"""

import json
import sys
from pathlib import Path

filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))

import grpc
from filter.v1 import filter_pb2, filter_pb2_grpc


VALID_CATEGORIES = [
    "neutral", "humor_sarcasm", "stress", "burnout",
    "depression", "harassment", "suicidal_ideation",
]
VALID_SEVERITIES = ["none", "early", "middle", "late"]


def _get_stub():
    channel = grpc.insecure_channel("localhost:50051")
    return filter_pb2_grpc.FilterServiceStub(channel), channel


def _assert_valid_response(resp):
    assert isinstance(resp.is_risk, bool)
    assert isinstance(resp.category, str)
    assert isinstance(resp.severity, str)
    assert 0.0 <= resp.category_confidence <= 1.0
    assert 0.0 <= resp.severity_confidence <= 1.0


def _as_enveloped_message(text: str, sent_at: str = "2026-04-07T00:00:00Z") -> str:
    """Build deterministic webhooks-style payload to stabilise confidence checks."""
    return json.dumps({"text": text, "meta": {"sent_at": sent_at}})


class TestClassifyMessagesBatch:

    def test_batch_single_matches_single_rpc(self):
        """A batch of 1 produces the same result as ClassifyMessage."""
        stub, ch = _get_stub()
        text = _as_enveloped_message("I feel overwhelmed and can't cope with work anymore")

        single = stub.ClassifyMessage(filter_pb2.ClassifyRequest(message=text))
        batch = stub.ClassifyMessages(filter_pb2.BatchClassifyRequest(messages=[text]))

        assert len(batch.results) == 1
        r = batch.results[0]
        assert r.is_risk == single.is_risk
        assert r.category == single.category
        assert abs(r.category_confidence - single.category_confidence) < 1e-3
        assert r.severity == single.severity
        assert abs(r.severity_confidence - single.severity_confidence) < 1e-3
        ch.close()

    def test_batch_multiple_messages(self):
        """Returns one result per input message."""
        stub, ch = _get_stub()
        messages = [
            "I feel great today, had a wonderful lunch",
            "I'm feeling so burned out I can't get out of bed",
            "The meeting is scheduled for 3pm tomorrow",
            "Nobody understands me and I feel completely alone",
        ]
        batch = stub.ClassifyMessages(filter_pb2.BatchClassifyRequest(messages=messages))
        assert len(batch.results) == len(messages)
        for r in batch.results:
            _assert_valid_response(r)
        ch.close()

    def test_batch_preserves_order(self):
        """Same message at different positions produces identical classification."""
        stub, ch = _get_stub()
        safe = "Let's schedule the quarterly review meeting"
        risk = "I can't stop crying and I feel hopeless"

        batch = stub.ClassifyMessages(
            filter_pb2.BatchClassifyRequest(messages=[safe, risk, safe])
        )
        assert len(batch.results) == 3
        assert batch.results[0].is_risk == batch.results[2].is_risk
        assert batch.results[0].category == batch.results[2].category
        assert abs(batch.results[0].category_confidence - batch.results[2].category_confidence) < 1e-6
        ch.close()

    def test_batch_empty_list(self):
        """Empty batch returns empty results."""
        stub, ch = _get_stub()
        batch = stub.ClassifyMessages(filter_pb2.BatchClassifyRequest(messages=[]))
        assert len(batch.results) == 0
        ch.close()

    def test_batch_empty_string(self):
        """Empty string classifies as neutral without crash."""
        stub, ch = _get_stub()
        batch = stub.ClassifyMessages(
            filter_pb2.BatchClassifyRequest(messages=["", "Hello world"])
        )
        assert len(batch.results) == 2
        assert batch.results[0].category == "neutral"
        assert batch.results[0].is_risk is False
        _assert_valid_response(batch.results[1])
        ch.close()

    def test_batch_long_message_sliding_window(self):
        """Long messages chunked via sliding window without error."""
        stub, ch = _get_stub()
        long_msg = "I've been feeling really stressed lately. " * 200
        batch = stub.ClassifyMessages(
            filter_pb2.BatchClassifyRequest(messages=[long_msg, "All good."])
        )
        assert len(batch.results) == 2
        _assert_valid_response(batch.results[0])
        assert "[Chunk" in batch.results[0].all_responses
        ch.close()

    def test_batch_consistency_with_single(self):
        """Every batch result matches its individual ClassifyMessage result."""
        stub, ch = _get_stub()
        messages = [
            _as_enveloped_message("The project deadline is next Friday"),
            _as_enveloped_message("I've been having panic attacks every morning"),
            _as_enveloped_message("Can someone bring snacks to the standup?"),
        ]
        singles = [
            stub.ClassifyMessage(filter_pb2.ClassifyRequest(message=m))
            for m in messages
        ]
        batch = stub.ClassifyMessages(filter_pb2.BatchClassifyRequest(messages=messages))

        for i, (s, b) in enumerate(zip(singles, batch.results)):
            assert s.is_risk == b.is_risk, f"is_risk mismatch at {i}"
            assert s.category == b.category, f"category mismatch at {i}"
            assert abs(s.category_confidence - b.category_confidence) < 1e-3
            assert s.severity == b.severity, f"severity mismatch at {i}"
        ch.close()

    def test_batch_moderate_size(self):
        """20 messages processed without timeout."""
        stub, ch = _get_stub()
        messages = [f"Test message number {i} about work" for i in range(20)]
        batch = stub.ClassifyMessages(filter_pb2.BatchClassifyRequest(messages=messages))
        assert len(batch.results) == 20
        for r in batch.results:
            _assert_valid_response(r)
        ch.close()

    def test_batch_all_responses_populated(self):
        """Non-empty messages produce all_responses strings."""
        stub, ch = _get_stub()
        batch = stub.ClassifyMessages(
            filter_pb2.BatchClassifyRequest(messages=[
                "I'm worried about my mental health",
                "Team lunch at noon",
            ])
        )
        for r in batch.results:
            assert r.all_responses is not None
            assert len(r.all_responses) > 0
        ch.close()


if __name__ == "__main__":
    print("Running batch classification tests...")
    t = TestClassifyMessagesBatch()
    for name in sorted(dir(t)):
        if name.startswith("test_"):
            print(f"\n{'='*60}\nRunning {name}...")
            getattr(t, name)()
            print(f"✓ {name} passed")
    print(f"\n{'='*60}\nAll batch tests passed!")
