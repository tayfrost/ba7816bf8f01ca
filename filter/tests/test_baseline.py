"""
Unit tests for the keyword-based heuristic classification function.
Tests regex-based classification and risk category priority logic.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import pytest

# Add scripts directory to path to test baseline
sys.path.append(str(Path(__file__).parent.parent / "scripts"))

from baseline_keyword import classify_message


@pytest.mark.parametrize(
    "text,expected_label",
    [
        ("I am going to have lunch now.", 0),  # Neutral
        (
            "I am so depressed, I want to end it all.",
            6,
        ),  # Suicidal (heuiristic high priority)
        ("I feel so burnt out and exhausted.", 3),  # Burnout
        ("You are so incompetent, shut up!", 5),  # Harassment
        (
            "I am under so much stress because you are worthless.",
            5,
        ),  # Priority: harassment > stress
        ("hahaha that is so funny lol", 1),  # Humor
        ("The pressure of this deadline is too much stress.", 2),  # Stress
        ("I feel hopeless and sad all day.", 4),  # Depression
    ],
)
def test_classify_message(text, expected_label):
    """Test message classification with various risk categories and priorities."""
    assert classify_message(text) == expected_label
