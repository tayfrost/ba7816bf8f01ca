"""
Pytest configuration for inference tests.

This conftest handles setup/teardown and shared fixtures for inference testing.
"""

import pytest
import sys
from pathlib import Path

# Add parent directories to path for imports
filter_dir = Path(__file__).parent.parent
sys.path.insert(0, str(filter_dir / "generated"))
sys.path.insert(0, str(filter_dir))


@pytest.fixture(scope="session")
def grpc_server_address():
    """Provide gRPC server address for tests."""
    return "localhost:50051"


@pytest.fixture(scope="session")
def test_messages():
    """Provide common test messages for inference tests."""
    return [
        "Just had another amazing day at work! The team is fantastic.",
        "I'm feeling overwhelmed with deadlines and can't seem to catch up.",
        "I'm completely burned out and don't want to work anymore.",
        "Feeling really down lately, nothing seems to help.",
        "This harassment needs to stop immediately.",
    ]


@pytest.fixture(scope="session")
def model_variants():
    """Provide list of model variants to test."""
    return ["fp32", "fp16", "dynamic_int8", "static_int8"]
