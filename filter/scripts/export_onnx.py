"""
Export trained PyTorch model to ONNX format.

This script loads the production model (with LoRA adapters merged)
and exports it to ONNX format for efficient inference.
"""

import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from services.model_factory import load_production_model


def export_to_onnx(
    output_path: str = "models/sentinelai_model.onnx",
    opset_version: int = 14,
):
    """
    Export the production model to ONNX format.
    
    Args:
        output_path: Path where ONNX model will be saved
        opset_version: ONNX opset version (14+ for transformers)
    """
    print("Loading production model...")
    device = torch.device("cpu")  # Export on CPU for compatibility
    model = load_production_model(device=device)
    
    # Merge LoRA weights into base model for export
    print("Merging LoRA adapters...")
    model.bert = model.bert.merge_and_unload()
    
    # Load tokenizer for dummy input
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    
    # Create dummy input
    dummy_text = "This is a sample message for ONNX export."
    inputs = tokenizer(
        dummy_text,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )
    
    dummy_input_ids = inputs["input_ids"].to(device)
    dummy_attention_mask = inputs["attention_mask"].to(device)
    
    # Export to ONNX
    output_file = Path(__file__).parent.parent / output_path
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
    
    # Export tokenizer
    tokenizer_dir = output_file.parent / "tokenizer"
    tokenizer_dir.mkdir(exist_ok=True)
    tokenizer.save_pretrained(str(tokenizer_dir))
    print(f"✓ Tokenizer saved to {tokenizer_dir}")
    
    return str(output_file)


if __name__ == "__main__":
    export_to_onnx()
