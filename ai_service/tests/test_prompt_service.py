"""Tests for prompt service versioning and loading."""

import pytest
from pathlib import Path
from services.prompt_service import PromptService


def test_prompt_service_initialization():
    """Test PromptService initializes correctly."""
    service = PromptService()
    assert service.prompts_dir.exists()


def test_parse_version():
    """Test version parsing from filenames."""
    service = PromptService()
    assert service._parse_version("system_prompt_v1.0.0.txt") == (1, 0, 0)
    assert service._parse_version("system_prompt_v2.5.3.txt") == (2, 5, 3)
    assert service._parse_version("no_version.txt") == (0, 0, 0)


def test_get_latest_version():
    """Test finding latest version."""
    service = PromptService()
    latest = service.get_latest_version()
    assert latest is not None
    assert "system_prompt" in latest
    assert ".txt" in latest


def test_load_latest_prompt():
    """Test loading the latest prompt."""
    service = PromptService()
    prompt = service.load_prompt()
    assert len(prompt) > 0
    assert "Mental Health" in prompt
    assert "Risk Assessment" in prompt


def test_load_specific_version():
    """Test loading a specific version of prompt."""
    service = PromptService()
    prompt = service.load_prompt_by_version("1.0.0")
    assert len(prompt) > 0
    assert "stress_level" in prompt
    assert "suicide_risk" in prompt
    assert "burnout_score" in prompt


def test_list_available_prompts():
    """Test listing all available prompts."""
    service = PromptService()
    prompts = service.list_available_prompts()
    assert len(prompts) > 0
    assert all("filename" in p for p in prompts)
    assert all("version" in p for p in prompts)


def test_prompt_content_requirements():
    """Test that the grade_message system prompt contains all scoring dimensions."""
    service = PromptService()
    prompt = service.load_prompt(subfolder="grade_message")

    # These must match the DB incident_scores columns and MentalHealthScore fields
    required_dimensions = [
        "neutral_score",
        "humor_sarcasm_score",
        "stress_score",
        "burnout_score",
        "depression_score",
        "harassment_score",
        "suicidal_ideation_score",
    ]

    for dimension in required_dimensions:
        assert dimension in prompt, f"Missing dimension in grade_message prompt: {dimension}"

    assert "risk" in prompt.lower()


def test_root_system_prompt_content():
    """Test that the root system prompt contains risk assessment guidance."""
    service = PromptService()
    prompt = service.load_prompt()

    assert "Risk Confirmation" in prompt or "risk" in prompt.lower()
    assert "HR" in prompt or "recommendations" in prompt.lower()


def test_load_nonexistent_prompt():
    """Test error handling for non-existent prompt."""
    service = PromptService()
    with pytest.raises(FileNotFoundError):
        service.load_prompt("nonexistent_v99.99.99.txt")
