"""
Unit tests for the DualHeadBERTClassifier.
Tests initialization, forward pass logic, and weight loading for the real production model.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path
import torch

# Add parent directory to path to allow importing from models and services
sys.path.append(str(Path(__file__).parent.parent))

from peft import PeftModel, LoraConfig, get_peft_model
from models.dual_head_classifier import DualHeadBERTClassifier

def test_model_initialization():
    """Test that the model initialises correctly with dual heads using the production base."""
    model = DualHeadBERTClassifier(model_name="bert-base-uncased")

    assert isinstance(model.category_classifier, torch.nn.Linear)
    assert isinstance(model.severity_classifier, torch.nn.Linear)
    assert model.category_classifier.out_features == 7
    assert model.severity_classifier.out_features == 4
    assert model.bert.config._name_or_path == "bert-base-uncased" # pylint: disable=protected-access

def test_model_forward_pass():
    """Test the forward pass of the production model and output tensor shapes."""
    model = DualHeadBERTClassifier(model_name="bert-base-uncased")
    model.eval()

    batch_size = 2
    seq_len = 128 # Production max length
    input_ids = torch.randint(0, 30522, (batch_size, seq_len)) # BERT vocab range
    attention_mask = torch.ones((batch_size, seq_len))

    with torch.no_grad():
        cat_logits, sev_logits = model(input_ids, attention_mask)

    assert cat_logits.shape == (batch_size, 7)
    assert sev_logits.shape == (batch_size, 4)

def test_adapter_loading():
    """Test that the model structure is compatible with PEFT/LoRA adapters."""
    model = DualHeadBERTClassifier(model_name="bert-base-uncased")
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["query", "value"],
        lora_dropout=0.1,
        bias="none"
    )

    model.bert = get_peft_model(model.bert, lora_config)
    assert isinstance(model.bert, PeftModel)

    # Verify trainable parameters are restricted to LoRA (approx 0.28% as seen in training)
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    assert 300000 < trainable_params < 400000 # Matches our 303k count
    assert (trainable_params / total_params) < 0.01

def test_real_model_inference(real_model, tokenizer):
    """Test inference using the real trained production weights."""
    message = "I am feeling very burnt out and exhausted."

    inputs = tokenizer(
        message,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=128
    )

    with torch.no_grad():
        cat_logits, sev_logits = real_model(inputs["input_ids"], inputs["attention_mask"])

    cat_pred = torch.argmax(cat_logits, dim=1).item()
    sev_pred = torch.argmax(sev_logits, dim=1).item()

    # Verify we get valid class indices
    assert 0 <= cat_pred <= 6
    assert 0 <= sev_pred <= 3

    # Checking model is actually predicting with its trained weights
    assert cat_pred in [2, 3, 4]
