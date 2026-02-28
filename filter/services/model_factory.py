"""
Model factory for SentinelAI BERT Filter.

Centralises model instantiation, LoRA application, and weight loading logic.
Supports automatic checkpoint download from Hugging Face Hub.
Supports ONNX model loading for inference.
"""

# pylint: disable=wrong-import-position

import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoTokenizer

try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Ensure internal imports work regardless of execution context
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

import config
from models.dual_head_classifier import DualHeadBERTClassifier


def create_raw_model(model_name: str = config.MODEL_NAME) -> DualHeadBERTClassifier:
    """
    Initialises the base DualHeadBERTClassifier architecture.
    """
    return DualHeadBERTClassifier(
        model_name=model_name,
        num_category_classes=config.NUM_CATEGORY_CLASSES,
        num_severity_classes=config.NUM_SEVERITY_CLASSES,
    )


def get_lora_config() -> LoraConfig:
    """
    Returns the standardised LoraConfig for SentiBERT.
    """
    return LoraConfig(
        r=config.LORA_R,
        lora_alpha=config.LORA_ALPHA,
        target_modules=config.LORA_TARGET_MODULES,
        lora_dropout=config.LORA_DROPOUT,
        bias="none",
        task_type=TaskType.FEATURE_EXTRACTION,
    )


def load_production_model(
    device: Optional[torch.device] = None, force_download: bool = False
) -> DualHeadBERTClassifier:
    """
    Loads the full production model including LoRA adapters and trained heads.
    Automatically downloads the checkpoint from HF Hub if missing.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1. Initialise base architecture
    model = create_raw_model()

    # 2. Apply LoRA structure
    lora_config = get_lora_config()
    model.bert = get_peft_model(model.bert, lora_config)

    # 3. Resolve checkpoint path
    checkpoint_path = config.MODELS_DIR / config.CHECKPOINT_FILENAME

    # 4. Auto-download from HF if missing or forced
    if not checkpoint_path.exists() or force_download:
        print(f"Checkpoint not found locally. Downloading from {config.HF_REPO_ID}...")
        try:
            downloaded_path = hf_hub_download(
                repo_id=config.HF_REPO_ID,
                filename=config.CHECKPOINT_FILENAME,
                local_dir=str(config.MODELS_DIR),
            )
            checkpoint_path = Path(downloaded_path)
        except Exception as e:
            print(f"Error downloading from Hugging Face: {e}")
            raise FileNotFoundError(
                f"Could not load checkpoint from {checkpoint_path} or HF Hub."
            ) from e

    # 5. Load state dict
    print(f"Loading weights from {checkpoint_path}...")
    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )
    model.load_state_dict(checkpoint["model_state_dict"])

    model.to(device)
    model.eval()

    return model


def load_onnx_model_and_tokenizer(repo_id: str = None, use_gpu: bool = False):
    """
    Download and load ONNX model and tokenizer from HF Space for inference.
    
    Args:
        repo_id: HuggingFace model repo ID (uses HF_MODEL env var if None)
        use_gpu: Whether to use GPU for inference (requires onnxruntime-gpu)
    
    Returns:
        Tuple of (ONNX InferenceSession, tokenizer dict)
    """
    if ort is None:
        raise ImportError("onnxruntime not installed. Run: pip install onnxruntime")
    
    if repo_id is None:
        repo_id = os.environ.get("HF_MODEL")
        if not repo_id:
            raise ValueError("repo_id not provided and HF_MODEL env var not set")
    
    print(f"Downloading ONNX model from {repo_id}...")
    local_dir = config.MODELS_DIR / "onnx_cache"
    local_dir.mkdir(parents=True, exist_ok=True)
    
    onnx_path = hf_hub_download(
        repo_id=repo_id,
        filename="sentinelai_model.onnx",
        repo_type="model",
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    
    # Download .data file if exists
    try:
        hf_hub_download(
            repo_id=repo_id,
            filename="sentinelai_model.onnx.data",
            repo_type="model",
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )
    except Exception:
        pass
    
    # Download tokenizer files
    print(f"Downloading tokenizer from {repo_id}...")
    tokenizer_dir = local_dir / "tokenizer"
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            allow_patterns="tokenizer/*",
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )
        tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
        print(f"✓ Tokenizer loaded from {tokenizer_dir}")
    except Exception as e:
        print(f"Warning: Could not load tokenizer from HF: {e}")
        print(f"Falling back to loading from HuggingFace Hub...")
        tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else ["CPUExecutionProvider"]
    session = ort.InferenceSession(onnx_path, providers=providers)
    
    print(f"✓ ONNX model loaded from {onnx_path}")
    return session, tokenizer


# Backwards compatibility alias
def load_model_for_inference(repo_id: str = None, use_gpu: bool = False):
    """
    Backwards compatibility wrapper for load_onnx_model_and_tokenizer.
    Returns only the session (old behavior).
    """
    session, _ = load_onnx_model_and_tokenizer(repo_id, use_gpu)
    return session
