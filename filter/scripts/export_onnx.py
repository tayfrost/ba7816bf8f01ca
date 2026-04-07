"""
Export trained PyTorch model to ONNX format.

This script loads the production model (with LoRA adapters merged)
and exports it to ONNX format for efficient inference.

You must have the trained model checkpoint and LoRA adapters in place before running this script.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from services.model_factory import load_production_model


def export_to_onnx(
    opset_version: int = 14,
) -> str:
    """
    Export the production model to ONNX format.
    """
    print("=" * 80)
    print("SentiBERT ONNX Exporter")
    print("=" * 80)

    print("Loading production model...")
    device = torch.device("cpu")  # Export on CPU for compatibility
    model = load_production_model(device=device)

    # Merge LoRA weights into base model for export
    print("Merging LoRA adapters...")
    model.bert = model.bert.merge_and_unload()

    # Load tokenizer for dummy input and for export
    print(f"Loading tokenizer: {config.MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)

    # Create dummy input
    dummy_text = "This is a sample message for ONNX export."
    inputs = tokenizer(
        dummy_text,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    dummy_input_ids = inputs["input_ids"].to(device)
    dummy_attention_mask = inputs["attention_mask"].to(device)

    # Resolve output path using SSOT config
    output_file = config.MODELS_DIR / config.ONNX_MODEL_FILENAME
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting to ONNX: {output_file}")
    torch.onnx.export(
        model,
        (dummy_input_ids, dummy_attention_mask),
        str(output_file),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input_ids", "attention_mask"],
        output_names=["category_logits", "severity_logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence_length"},
            "attention_mask": {0: "batch_size", 1: "sequence_length"},
            "category_logits": {0: "batch_size"},
            "severity_logits": {0: "batch_size"},
        },
    )

    print(f"✓ Model exported successfully to {output_file}")
    print(f"  File size: {output_file.stat().st_size / (1024**2):.2f} MB")

    # Export tokenizer as well (k24000626's inference server API)
    tokenizer_dir = config.MODELS_DIR / config.TOKENIZER_DIRNAME
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving tokenizer files to: {tokenizer_dir}")
    tokenizer.save_pretrained(str(tokenizer_dir))

    print("=" * 80)
    return str(output_file)


if __name__ == "__main__":
    export_to_onnx()
