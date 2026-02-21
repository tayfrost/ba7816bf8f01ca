"""
Shared pytest fixtures and configuration for SentinelAI filter tests.
Provides sample data, tokenizers, and real production model loading logic.
"""

# pylint: disable=redefined-outer-name
# pylint: disable=wrong-import-position

# NOTE: Only ignore wrong import position if style is kept like this.

import json
import sys
from pathlib import Path

import pytest
import torch
from transformers import AutoTokenizer

# Add parent directory to path to allow importing from models and services
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.model_factory import load_production_model


@pytest.fixture
def sample_data():
    """Returns a list of sample dataset items."""
    return [
        {
            "message": "I am so stressed out with work.",
            "category": "stress",
            "stage": "early",
            "is_risk": 1,
        },
        {
            "message": "I am fine and happy.",
            "category": "neutral",
            "stage": "none",
            "is_risk": 0,
        },
        {
            "message": "I want to end it all.",
            "category": "suicidal_ideation",
            "stage": "late",
            "is_risk": 1,
        },
    ]


@pytest.fixture
def tokenizer():
    """Returns a BERT tokenizer."""
    return AutoTokenizer.from_pretrained(config.MODEL_NAME)


@pytest.fixture
def mock_dataset_files(tmp_path, sample_data):
    """Creates temporary JSON files for dataset loading tests."""
    v01_path = tmp_path / "sentinelai_dataset_v0.1.json"
    v02_path = tmp_path / "sentinelai_dataset_v0.2.json"

    # Create v0.1 with 3 items
    with open(v01_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    # Create v0.2 with 3 items
    with open(v02_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    return v01_path, v02_path


@pytest.fixture
def real_model():
    """Loads the real production model with trained weights. Handles auto-download."""
    device = torch.device("cpu")  # Test on CPU for stability
    return load_production_model(device=device)
