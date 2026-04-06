"""Test ONNX download and inference workflow via model factory."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from services.model_factory import load_onnx_model_and_tokenizer


def test_load_and_infer_onnx():
    """Test ONNX model loading and inference."""
    print("\n=== TEST: Download and Inference ===")

    # Load ONNX model and tokenizer
    session, tokenizer = load_onnx_model_and_tokenizer()
    assert session is not None, "Failed to load ONNX inference session"
    assert tokenizer is not None, "Failed to load tokenizer"

    # Prepare test input
    test_text = "I feel so overwhelmed with work lately."
    
    inputs = tokenizer(
        test_text,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="np"
    )

    # Run inference
    outputs = session.run(
        None,
        {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }
    )

    category_logits, severity_logits = outputs
    category_pred = np.argmax(category_logits, axis=1)[0]
    severity_pred = np.argmax(severity_logits, axis=1)[0]

    # Map back to labels
    category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
    severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}

    print(f"Input: '{test_text}'")
    print(f"Category: {category_labels[category_pred]}")
    print(f"Severity: {severity_labels[severity_pred]}")
    print("✓ Inference successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
