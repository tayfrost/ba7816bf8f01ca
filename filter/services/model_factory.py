"""
Model factory for SentinelAI BERT Filter.

Centralises model instantiation, LoRA application, and weight loading logic.
Supports automatic checkpoint download from Hugging Face Hub.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path
from typing import Optional

import torch
from huggingface_hub import hf_hub_download
from peft import LoraConfig, TaskType, get_peft_model

# Ensure internal imports work regardless of execution context
sys.path.append(str(Path(__file__).parent.parent))

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
