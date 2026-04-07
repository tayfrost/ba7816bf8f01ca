"""
Unit tests for the MentalHealthDataset and dataset loading services.
Tests data formatting, label encoding, and reproducible splitting.
"""

# pylint: disable=wrong-import-position

import sys
from collections.abc import Sized
from pathlib import Path
from typing import cast

import pytest

# Add parent directory to path to allow importing from models and services
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import (
    CATEGORY_MAP,
    SEVERITY_MAP,
    MentalHealthDataset,
    load_dataset,
)


def test_dataset_item_format(sample_data, tokenizer):
    """Test that the dataset returns the correct format for BERT."""
    max_length = 32
    dataset = MentalHealthDataset(sample_data, tokenizer, max_length=max_length)

    assert len(dataset) == len(sample_data)

    item = dataset[0]
    required_keys = [
        "input_ids",
        "attention_mask",
        "category_label",
        "severity_label",
        "is_risk",
    ]
    for key in required_keys:
        assert key in item

    assert item["input_ids"].shape == (max_length,)
    assert item["attention_mask"].shape == (max_length,)
    assert item["category_label"] == CATEGORY_MAP[sample_data[0]["category"]]
    assert item["severity_label"] == SEVERITY_MAP[sample_data[0]["stage"]]

    # Check for temporal context [YYYY-MM-DD HH:MM] prefix
    # BERT tokenizer adds spaces around brackets and punctuation
    decoded_text = tokenizer.decode(item["input_ids"], skip_special_tokens=True)
    import re
    assert re.search(r"\[\s*\d{4}\s*-\s*\d{2}\s*-\s*\d{2}\s*\d{2}\s*:\s*\d{2}\s*\]", decoded_text)


@pytest.mark.parametrize(
    "idx,expected_cat,expected_sev",
    [
        (1, CATEGORY_MAP["neutral"], SEVERITY_MAP["none"]),
        (2, CATEGORY_MAP["suicidal_ideation"], SEVERITY_MAP["late"]),
        (0, CATEGORY_MAP["stress"], SEVERITY_MAP["early"]),
    ],
)
def test_dataset_label_encoding(
    sample_data, tokenizer, idx, expected_cat, expected_sev
):
    """Test that labels are encoded correctly into indices using parametrisation."""
    dataset = MentalHealthDataset(sample_data, tokenizer)
    item = dataset[idx]
    assert item["category_label"].item() == expected_cat
    assert item["severity_label"].item() == expected_sev


def test_load_dataset_splits(mock_dataset_files):
    """Test that load_dataset correctly splits data into train/val/test using the prod backbone."""
    _, v02_path = mock_dataset_files

    # Use production model name to ensure tokenizer consistency
    train_loader, val_loader, test_loader, _ = load_dataset(
        dataset_path=str(v02_path),
        model_name=config.MODEL_NAME,
        train_split=0.6,
        val_split=0.2,
        mix_datasets=False,  # Simplified for the split logic test
    )

    # ``dataset`` is typed as ``Dataset[Unknown]`` by torch stubs, so cast to
    # ``Sized`` for the static checker before calling ``len``.
    total_samples = (
        len(cast(Sized, train_loader.dataset))
        + len(cast(Sized, val_loader.dataset))
        + len(cast(Sized, test_loader.dataset))
    )

    assert total_samples == 3
    assert len(train_loader) > 0
    assert len(test_loader) > 0
