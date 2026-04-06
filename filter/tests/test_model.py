"""
Unit tests for the DualHeadBERTClassifier.
Tests initialization, forward pass logic, and weight loading for the real production model.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import torch
from peft import PeftModel, get_peft_model

# Add parent directory to path to allow importing from models and services
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.model_factory import (
    create_raw_model,
    get_lora_config,
    resolve_onnx_variant_filename,
)


def test_model_initialization():
    """Test that the model initialises correctly with dual heads using the production base."""
    model = create_raw_model()

    assert isinstance(model.category_classifier, torch.nn.Linear)
    assert isinstance(model.severity_classifier, torch.nn.Linear)
    assert model.category_classifier.out_features == config.NUM_CATEGORY_CLASSES
    assert model.severity_classifier.out_features == config.NUM_SEVERITY_CLASSES

    # Accessing a protected attribute is OK in tests
    assert model.bert.config._name_or_path == config.MODEL_NAME # pylint: disable=protected-access


def test_model_forward_pass():
    """Test the forward pass of the production model and output tensor shapes."""
    model = create_raw_model()
    model.eval()

    batch_size = 2
    seq_len = config.MAX_LENGTH  # Production max length
    input_ids = torch.randint(0, 30522, (batch_size, seq_len))  # BERT vocab range
    attention_mask = torch.ones((batch_size, seq_len))

    with torch.no_grad():
        cat_logits, sev_logits = model(input_ids, attention_mask)

    assert cat_logits.shape == (batch_size, config.NUM_CATEGORY_CLASSES)
    assert sev_logits.shape == (batch_size, config.NUM_SEVERITY_CLASSES)


def test_adapter_loading():
    """Test that the model structure is compatible with PEFT/LoRA adapters."""
    model = create_raw_model()
    lora_config = get_lora_config()

    model.bert = get_peft_model(model.bert, lora_config)
    assert isinstance(model.bert, PeftModel)

    # Verify trainable parameters are restricted to LoRA (approx 0.28% as seen in training)
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    assert 300000 < trainable_params < 400000  # Matches our 303k count
    assert (trainable_params / total_params) < 0.01


def test_real_model_inference(real_model, tokenizer):
    """Test inference using the real trained production weights."""
    message = "I am feeling very burnt out and exhausted."

    inputs = tokenizer(
        message,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=config.MAX_LENGTH,
    )

    with torch.no_grad():
        cat_logits, sev_logits = real_model(
            inputs["input_ids"], inputs["attention_mask"]
        )

    cat_pred = torch.argmax(cat_logits, dim=1).item()
    sev_pred = torch.argmax(sev_logits, dim=1).item()

    # Verify we get valid class indices
    assert 0 <= cat_pred <= 6
    assert 0 <= sev_pred <= 3

    # Checking model is actually predicting with its trained weights
    assert cat_pred in [2, 3, 4]


def test_resolve_onnx_variant_filename_known_variants():
    """Known ONNX variant keys should map to canonical artifact names."""
    assert resolve_onnx_variant_filename("fp32") == config.ONNX_MODEL_FILENAME
    assert resolve_onnx_variant_filename("base") == config.ONNX_MODEL_FILENAME
    assert resolve_onnx_variant_filename("fp16") == config.ONNX_FP16_MODEL_FILENAME
    assert (
        resolve_onnx_variant_filename("dynamic_int8")
        == config.ONNX_DYNAMIC_INT8_MODEL_FILENAME
    )
    assert (
        resolve_onnx_variant_filename("static-int8")
        == config.ONNX_STATIC_INT8_MODEL_FILENAME
    )


def test_resolve_onnx_variant_filename_custom_filename_and_invalid_key():
    """Custom `.onnx` filename should pass, invalid key should fail."""
    custom = "my_experimental_quant.onnx"
    assert resolve_onnx_variant_filename(custom) == custom

    try:
        resolve_onnx_variant_filename("int4")
        assert False, "Expected ValueError for unsupported ONNX variant"
    except ValueError:
        pass
