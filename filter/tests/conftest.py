"""
Shared pytest fixtures and configuration for SentinelAI filter tests.
Provides sample data, tokenizers, and real production model loading logic.
"""

# pylint: disable=redefined-outer-name
# pylint: disable=wrong-import-position

# NOTE: Only ignore wrong import position if style is kept like this.

import sys
from pathlib import Path
import json
import torch

import pytest
from transformers import AutoTokenizer

# Add parent directory to path to allow importing from models and services
sys.path.append(str(Path(__file__).parent.parent))

from peft import LoraConfig, get_peft_model, TaskType
from models.dual_head_classifier import DualHeadBERTClassifier

@pytest.fixture
def sample_data():
    """Returns a list of sample dataset items."""
    return [
        {
            "message": "I am so stressed out with work.",
            "category": "stress",
            "stage": "early",
            "is_risk": 1
        },
        {
            "message": "I am fine and happy.",
            "category": "neutral",
            "stage": "none",
            "is_risk": 0
        },
        {
            "message": "I want to end it all.",
            "category": "suicidal_ideation",
            "stage": "late",
            "is_risk": 1
        }
    ]

@pytest.fixture
def tokenizer():
    """Returns a BERT tokenizer."""
    return AutoTokenizer.from_pretrained("bert-base-uncased")

@pytest.fixture
def mock_dataset_files(tmp_path, sample_data):
    """Creates temporary JSON files for dataset loading tests."""
    v01_path = tmp_path / "sentinelai_dataset_v0.1.json"
    v02_path = tmp_path / "sentinelai_dataset_v0.2.json"

    # Create v0.1 with 3 items
    with open(v01_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    # Create v0.2 with 3 items
    with open(v02_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    return v01_path, v02_path

@pytest.fixture
def trained_model_path():
    """Returns the path to the real production model checkpoint."""
    return Path(__file__).parent.parent / "models" / "dual_head_classifier.pt"

@pytest.fixture
def real_model(trained_model_path):
    """Loads the real production model with trained weights. Hard failure if weights are missing."""
    if not trained_model_path.exists():
        pytest.fail(f"Production model checkpoint not found at {trained_model_path}. "
                    "Tests requiring the real model cannot proceed.")

    device = torch.device("cpu") # Test on CPU for stability
    model = DualHeadBERTClassifier(model_name="bert-base-uncased")

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["query", "value"],
        lora_dropout=0.1,
        bias="none",
        task_type=TaskType.FEATURE_EXTRACTION
    )
    model.bert = get_peft_model(model.bert, lora_config)

    checkpoint = torch.load(trained_model_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])

    model.eval()
    return model
