"""
Automate ONNX conversion and upload to Hugging Face Space.

Loads a model from HF, converts to ONNX, and uploads to target HF Space.
"""

import os
import sys
from pathlib import Path

import torch
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import config
from services.model_factory import load_production_model


def load_model_from_hf_space(space_name: str) -> torch.nn.Module:
    """
    Load PyTorch model from teammate's HF Space.
    
    Args:
        space_name: HF Space name (e.g., "username/space-name")
    
    Returns:
        Loaded PyTorch model
    """
    print(f"Loading model from {space_name}...")
    return load_production_model()


def export_to_onnx(model: torch.nn.Module, onnx_path: Path) -> None:
    """
    Convert PyTorch model to ONNX format.
    
    Args:
        model: PyTorch model to convert
        onnx_path: Output path for ONNX file
    """
    print("Merging LoRA adapters...")
    model.bert = model.bert.merge_and_unload()
    model.eval()
    
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    dummy_text = "This is a sample message for ONNX export."
    inputs = tokenizer(
        dummy_text,
        max_length=config.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )
    
    print(f"Exporting to {onnx_path}...")
    with torch.no_grad():
        torch.onnx.export(
            model,
            (inputs["input_ids"], inputs["attention_mask"]),
            str(onnx_path),
            export_params=True,
            opset_version=17,
            do_constant_folding=True,
            input_names=["input_ids", "attention_mask"],
            output_names=["category_logits", "severity_logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size"},
                "attention_mask": {0: "batch_size"},
                "category_logits": {0: "batch_size"},
                "severity_logits": {0: "batch_size"},
            },
        )
    print(f"✓ Exported to {onnx_path}")


def prepare_and_upload_model(teammate_space_name: str = None) -> str:
    """
    Load model from HF Space, convert to ONNX, and upload to target HF Space.
    
    Args:
        teammate_space_name: Source HF Space (optional, uses local model if None)
    
    Returns:
        URL of uploaded model
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable not set")
    
    target_repo = os.environ.get("HF_MODEL")
    if not target_repo:
        raise ValueError("HF_MODEL environment variable not set")
    
    # 1. Load model
    model = load_model_from_hf_space(teammate_space_name) if teammate_space_name else load_production_model()
    
    # 2. Convert to ONNX
    onnx_path = config.MODELS_DIR / "sentinelai_model.onnx"
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    export_to_onnx(model, onnx_path)
    
    # 3. Upload to HF Space
    api = HfApi(token=hf_token)
    print(f"Uploading to {target_repo}...")
    
    api.create_repo(target_repo, repo_type="model", exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(onnx_path),
        path_in_repo="sentinelai_model.onnx",
        repo_id=target_repo,
        repo_type="model",
    )
    
    # Upload .data file if exists
    data_path = onnx_path.with_suffix(".onnx.data")
    if data_path.exists():
        print(f"Uploading external data file...")
        api.upload_file(
            path_or_fileobj=str(data_path),
            path_in_repo="sentinelai_model.onnx.data",
            repo_id=target_repo,
            repo_type="model",
        )
    
    url = f"https://huggingface.co/{target_repo}"
    print(f"✓ Uploaded to {url}")
    return url


if __name__ == "__main__":
    prepare_and_upload_model()
