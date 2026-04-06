"""Tests for ONNX quantized model variants.

Ports intent from legacy inference variant tests while aligning with the
current canonical architecture (single gRPC endpoint + direct ONNX artifacts).
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
from transformers import AutoTokenizer

import config


def _existing_variant_paths(onnx_model_variant_filenames: dict[str, str]) -> dict[str, Path]:
    """Return only ONNX variant files currently present on disk."""
    existing: dict[str, Path] = {}
    for variant, filename in onnx_model_variant_filenames.items():
        path = config.MODELS_DIR / filename
        if path.exists():
            existing[variant] = path
    return existing


def _run_single_inference(session: ort.InferenceSession, tokenizer, text: str):
    """Run one inference pass and return logits."""
    inputs = tokenizer(
        text,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="np",
    )
    outputs = session.run(
        None,
        {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        },
    )
    return outputs[0], outputs[1]


def test_quantized_variants_load_and_infer(onnx_model_variant_filenames, inference_test_messages):
    """Each available ONNX variant should load and produce valid logits."""
    existing = _existing_variant_paths(onnx_model_variant_filenames)
    if not existing:
        pytest.skip("No ONNX model artifacts present under filter/models")

    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)

    for variant, model_path in existing.items():
        session = ort.InferenceSession(str(model_path))

        input_names = [inp.name for inp in session.get_inputs()]
        output_names = [out.name for out in session.get_outputs()]
        assert "input_ids" in input_names, f"{variant}: missing input_ids input"
        assert "attention_mask" in input_names, f"{variant}: missing attention_mask input"
        assert "category_logits" in output_names, f"{variant}: missing category_logits output"
        assert "severity_logits" in output_names, f"{variant}: missing severity_logits output"

        category_logits, severity_logits = _run_single_inference(
            session, tokenizer, inference_test_messages[1]
        )

        assert category_logits.shape == (1, config.NUM_CATEGORY_CLASSES), (
            f"{variant}: invalid category logits shape {category_logits.shape}"
        )
        assert severity_logits.shape == (1, config.NUM_SEVERITY_CLASSES), (
            f"{variant}: invalid severity logits shape {severity_logits.shape}"
        )

        assert np.isfinite(category_logits).all(), f"{variant}: category logits contain NaN/Inf"
        assert np.isfinite(severity_logits).all(), f"{variant}: severity logits contain NaN/Inf"


def test_quantized_variants_prediction_sanity(onnx_model_variant_filenames, inference_test_messages):
    """All available variants should return valid label indices for the same input."""
    existing = _existing_variant_paths(onnx_model_variant_filenames)
    if len(existing) < 2:
        pytest.skip("Need at least two ONNX variants for cross-variant sanity check")

    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    test_text = inference_test_messages[2]

    predictions = {}
    for variant, model_path in existing.items():
        session = ort.InferenceSession(str(model_path))
        category_logits, severity_logits = _run_single_inference(session, tokenizer, test_text)

        category_pred = int(np.argmax(category_logits, axis=1)[0])
        severity_pred = int(np.argmax(severity_logits, axis=1)[0])

        assert 0 <= category_pred < config.NUM_CATEGORY_CLASSES
        assert 0 <= severity_pred < config.NUM_SEVERITY_CLASSES

        predictions[variant] = (category_pred, severity_pred)

    # We intentionally do not enforce identical predictions across quantized variants.
    assert len(predictions) >= 2
