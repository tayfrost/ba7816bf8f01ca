"""Tests for project setup configuration."""

import os
from pathlib import Path


def test_requirements_file_exists():
    """Test that requirements.txt exists and has expected dependencies."""
    req_file = Path(__file__).parent.parent / "requirements.txt"
    assert req_file.exists()
    content = req_file.read_text()
    assert "langgraph" in content
    assert "pydantic" in content
    assert "fastapi" in content
    assert "uvicorn" in content


def test_dockerfile_exists():
    """Test that Dockerfile exists and has expected configuration."""
    dockerfile = Path(__file__).parent.parent / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text()
    assert "FROM python" in content
    assert "EXPOSE 8001" in content
    assert "uvicorn" in content
