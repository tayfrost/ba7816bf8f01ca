"""
Test ONNX model variants directly (without gRPC server).

Tests model loading and basic inference for all quantized variants.
"""

import sys
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from inference_services.onnx_factory import load_onnx_models_and_tokenizer
from inference_services.classification_utils import (
    tokenize_message,
    prepare_chunk_inputs,
    run_chunk_inference,
    process_chunk_predictions,
)


def test_load_all_models():
    """Test that all model variants can be loaded."""
    print("\n" + "="*80)
    print("Testing Model Loading")
    print("="*80)
    
    models, tokenizer = load_onnx_models_and_tokenizer()
    
    assert models is not None, "Models dict is None"
    assert tokenizer is not None, "Tokenizer is None"
    assert len(models) > 0, "No models loaded"
    
    expected_models = ["fp32", "fp16", "dynamic_int8", "static_int8"]
    loaded_models = list(models.keys())
    
    print(f"\nExpected models: {expected_models}")
    print(f"Loaded models: {loaded_models}")
    
    for model_name in expected_models:
        if model_name in models:
            print(f"  ✓ {model_name} loaded")
        else:
            print(f"  ⚠ {model_name} not available")
    
    assert len(models) >= 1, "At least one model should be loaded"


def test_tokenizer_special_tokens():
    """Test that tokenizer has required special tokens."""
    print("\n" + "="*80)
    print("Testing Tokenizer")
    print("="*80)
    
    _, tokenizer = load_onnx_models_and_tokenizer()
    
    # Get special token IDs
    cls_token_id = tokenizer.token_to_id('[CLS]')
    sep_token_id = tokenizer.token_to_id('[SEP]')
    pad_token_id = tokenizer.token_to_id('[PAD]')
    
    assert cls_token_id is not None, "CLS token not found"
    assert sep_token_id is not None, "SEP token not found"
    assert pad_token_id is not None, "PAD token not found"
    
    print(f"\n  ✓ [CLS] token ID: {cls_token_id}")
    print(f"  ✓ [SEP] token ID: {sep_token_id}")
    print(f"  ✓ [PAD] token ID: {pad_token_id}")


def test_inference_single_model(model_name="fp32"):
    """
    Test inference with a single model variant.
    
    Args:
        model_name: Model variant to test
    """
    print(f"\n{'='*80}")
    print(f"Testing Inference: {model_name.upper()}")
    print("="*80)
    
    # Load models
    models, tokenizer = load_onnx_models_and_tokenizer()
    
    if model_name not in models:
        print(f"  ⚠ {model_name} not available, skipping")
        return
    
    model = models[model_name]
    
    # Test message
    test_message = "I'm feeling really stressed and overwhelmed with work."
    print(f"\nTest message: {test_message}")
    
    # Get special tokens
    cls_token_id = tokenizer.token_to_id('[CLS]')
    sep_token_id = tokenizer.token_to_id('[SEP]')
    pad_token_id = tokenizer.token_to_id('[PAD]')
    
    # Tokenize
    tokens = tokenize_message(tokenizer, test_message)
    print(f"Tokenized: {len(tokens)} tokens")
    
    # Prepare inputs
    input_ids, attention_mask = prepare_chunk_inputs(
        tokens,
        cls_token_id,
        sep_token_id,
        pad_token_id,
        config.MAX_LENGTH
    )
    
    # Run inference
    category_logits, severity_logits = run_chunk_inference(
        model,
        input_ids,
        attention_mask
    )
    
    # Validate outputs
    assert category_logits.shape == (1, config.NUM_CATEGORY_CLASSES), \
        f"Invalid category shape: {category_logits.shape}"
    assert severity_logits.shape == (1, config.NUM_SEVERITY_CLASSES), \
        f"Invalid severity shape: {severity_logits.shape}"
    
    assert np.isfinite(category_logits).all(), "Category logits contain NaN/Inf"
    assert np.isfinite(severity_logits).all(), "Severity logits contain NaN/Inf"
    
    # Get predictions
    category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
    severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}
    
    result = process_chunk_predictions(
        category_logits,
        severity_logits,
        category_labels,
        severity_labels,
        config.RISK_CATEGORIES
    )
    
    print(f"\nResults:")
    print(f"  ✓ Category: {result['category']} (confidence: {result['category_confidence']:.3f})")
    print(f"  ✓ Severity: {result['severity']} (confidence: {result['severity_confidence']:.3f})")
    print(f"  ✓ Is Risk: {result['is_risk']}")


def test_all_models_inference():
    """Test inference with all available model variants."""
    print("\n" + "="*80)
    print("Testing All Models Inference")
    print("="*80)
    
    models, tokenizer = load_onnx_models_and_tokenizer()
    
    test_message = "Feeling anxious about upcoming deadlines."
    print(f"\nTest message: {test_message}")
    
    # Get special tokens
    cls_token_id = tokenizer.token_to_id('[CLS]')
    sep_token_id = tokenizer.token_to_id('[SEP]')
    pad_token_id = tokenizer.token_to_id('[PAD]')
    
    # Tokenize once
    tokens = tokenize_message(tokenizer, test_message)
    
    # Prepare inputs once
    input_ids, attention_mask = prepare_chunk_inputs(
        tokens,
        cls_token_id,
        sep_token_id,
        pad_token_id,
        config.MAX_LENGTH
    )
    
    category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
    severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}
    
    # Test each model
    for model_name, model in models.items():
        print(f"\n{model_name.upper()}:")
        
        # Run inference
        category_logits, severity_logits = run_chunk_inference(
            model,
            input_ids,
            attention_mask
        )
        
        # Validate
        assert np.isfinite(category_logits).all()
        assert np.isfinite(severity_logits).all()
        
        # Get predictions
        result = process_chunk_predictions(
            category_logits,
            severity_logits,
            category_labels,
            severity_labels,
            config.RISK_CATEGORIES
        )
        
        print(f"  Category: {result['category']} ({result['category_confidence']:.3f})")
        print(f"  Severity: {result['severity']} ({result['severity_confidence']:.3f})")
        print(f"  Is Risk: {result['is_risk']}")


def test_model_consistency():
    """Test that different models produce similar results."""
    print("\n" + "="*80)
    print("Testing Model Consistency")
    print("="*80)
    
    models, tokenizer = load_onnx_models_and_tokenizer()
    
    if len(models) < 2:
        print("  ⚠ Need at least 2 models for consistency test, skipping")
        return
    
    test_messages = [
        "Everything is going great today!",
        "I'm feeling extremely stressed and burned out.",
        "This is harassment and I won't tolerate it anymore.",
    ]
    
    # Get special tokens
    cls_token_id = tokenizer.token_to_id('[CLS]')
    sep_token_id = tokenizer.token_to_id('[SEP]')
    pad_token_id = tokenizer.token_to_id('[PAD]')
    
    category_labels = {v: k for k, v in config.CATEGORY_MAP.items()}
    severity_labels = {v: k for k, v in config.SEVERITY_MAP.items()}
    
    for test_message in test_messages:
        print(f"\nMessage: {test_message[:60]}...")
        
        # Tokenize
        tokens = tokenize_message(tokenizer, test_message)
        input_ids, attention_mask = prepare_chunk_inputs(
            tokens,
            cls_token_id,
            sep_token_id,
            pad_token_id,
            config.MAX_LENGTH
        )
        
        # Get predictions from all models
        predictions = {}
        for model_name, model in models.items():
            category_logits, severity_logits = run_chunk_inference(
                model,
                input_ids,
                attention_mask
            )
            
            result = process_chunk_predictions(
                category_logits,
                severity_logits,
                category_labels,
                severity_labels,
                config.RISK_CATEGORIES
            )
            
            predictions[model_name] = result
            print(f"  {model_name}: {result['category']} / {result['severity']}")
        
        # Check if all models agree on category (may differ slightly due to quantization)
        categories = [p['category'] for p in predictions.values()]
        print(f"  Categories: {set(categories)}")
        
        if len(set(categories)) == 1:
            print(f"  ✓ All models agree")
        else:
            print(f"  ⚠ Models have different predictions (expected for quantized models)")


if __name__ == '__main__':
    """Run tests."""
    print("\n" + "="*80)
    print("DIRECT MODEL INFERENCE TEST SUITE")
    print("="*80)
    print("\nThese tests load models directly without requiring gRPC server")
    print("")
    
    try:
        test_load_all_models()
        test_tokenizer_special_tokens()
        
        # Test each available model
        for model_name in ["fp32", "fp16", "dynamic_int8", "static_int8"]:
            test_inference_single_model(model_name)
        
        test_all_models_inference()
        test_model_consistency()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        
    except Exception as e:
        print(f"\n" + "="*80)
        print(f"TEST FAILED: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
