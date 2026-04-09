"""Test ONNX model inference."""

import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
from transformers import AutoTokenizer

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config


def test_onnx_model_inference():
    """Test that ONNX model produces valid outputs."""
    # Load ONNX model
    model_path = config.MODELS_DIR / config.ONNX_MODEL_FILENAME
    if not model_path.exists():
        pytest.skip(f"ONNX model artifact missing at {model_path}")

    session = ort.InferenceSession(str(model_path))

    # Verify input/output names
    input_names = [inp.name for inp in session.get_inputs()]
    output_names = [out.name for out in session.get_outputs()]

    assert "input_ids" in input_names
    assert "attention_mask" in input_names
    assert "category_logits" in output_names
    assert "severity_logits" in output_names

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)

    # Test message
    test_message = "I'm feeling really anxious and can't sleep at night."

    # Tokenize
    inputs = tokenizer(
        test_message,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="np"
    )

    # Run inference
    outputs = session.run(
        output_names,
        {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }
    )

    category_logits, severity_logits = outputs

    # Assertions
    assert category_logits.shape == (1, config.NUM_CATEGORY_CLASSES), \
        f"Expected category shape (1, {config.NUM_CATEGORY_CLASSES}), got {category_logits.shape}"

    assert severity_logits.shape == (1, config.NUM_SEVERITY_CLASSES), \
        f"Expected severity shape (1, {config.NUM_SEVERITY_CLASSES}), got {severity_logits.shape}"

    # Check logits are finite
    assert np.isfinite(category_logits).all(), "Category logits contain NaN/Inf"
    assert np.isfinite(severity_logits).all(), "Severity logits contain NaN/Inf"

    # Get predictions
    category_pred = np.argmax(category_logits, axis=1)[0]
    severity_pred = np.argmax(severity_logits, axis=1)[0]

    # Check predictions are valid indices
    assert 0 <= category_pred < config.NUM_CATEGORY_CLASSES
    assert 0 <= severity_pred < config.NUM_SEVERITY_CLASSES

    # Get confidence scores (softmax)
    category_probs = np.exp(category_logits) / np.sum(np.exp(category_logits), axis=1)
    severity_probs = np.exp(severity_logits) / np.sum(np.exp(severity_logits), axis=1)

    category_confidence = category_probs[0, category_pred]
    severity_confidence = severity_probs[0, severity_pred]

    # Reverse mappings
    idx_to_category = {v: k for k, v in config.CATEGORY_MAP.items()}
    idx_to_severity = {v: k for k, v in config.SEVERITY_MAP.items()}

    print(f"✓ ONNX inference successful")
    print(f"  Input: {test_message}")
    print(f"  Category: {idx_to_category[category_pred]} (confidence: {category_confidence:.3f})")
    print(f"  Severity: {idx_to_severity[severity_pred]} (confidence: {severity_confidence:.3f})")
    print(f"  Model size: {model_path.stat().st_size / (1024**2):.2f} MB")


if __name__ == "__main__":
    test_onnx_model_inference()
