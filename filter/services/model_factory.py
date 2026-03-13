"""
Model factory for SentinelAI BERT Filter.

Centralises model instantiation, LoRA application, and weight loading logic.
Supports automatic checkpoint download from Hugging Face Hub.
Supports ONNX model loading for efficient inference.
"""

# pylint: disable=wrong-import-position
# pylint: disable=import-outside-toplevel

# NOTE: Only respect disabled linting if you are adhering to lazy importing in retrospect.

import sys
from pathlib import Path
from typing import Any, Optional, Tuple

from huggingface_hub import hf_hub_download, snapshot_download

try:
    import onnxruntime as ort
except ImportError:
    ort = None

try:
    from tokenizers import Tokenizer
except ImportError:
    Tokenizer = None

# Ensure internal imports work regardless of execution context
sys.path.append(str(Path(__file__).parent.parent))

import config


def create_raw_model(model_name: str = config.MODEL_NAME) -> Any:
    """
    Initialises the base DualHeadBERTClassifier architecture.
    """
    from models.dual_head_classifier import DualHeadBERTClassifier

    return DualHeadBERTClassifier(
        model_name=model_name,
        num_category_classes=config.NUM_CATEGORY_CLASSES,
        num_severity_classes=config.NUM_SEVERITY_CLASSES,
    )


def get_lora_config() -> Any:
    """
    Returns the standardised LoraConfig for SentiBERT.
    """
    from peft import LoraConfig, TaskType

    return LoraConfig(
        r=config.LORA_R,
        lora_alpha=config.LORA_ALPHA,
        target_modules=config.LORA_TARGET_MODULES,
        lora_dropout=config.LORA_DROPOUT,
        bias="none",
        task_type=TaskType.FEATURE_EXTRACTION,
    )


def load_production_model(
    device: Optional[Any] = None, force_download: bool = False
) -> Any:
    """
    Loads the full production model including LoRA adapters and trained heads.
    Automatically downloads the checkpoint from HF Hub if missing.
    """
    import torch
    from peft import get_peft_model

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1. Initialise base architecture
    model = create_raw_model()

    # 2. Apply LoRA structure
    lora_config = get_lora_config()
    model.bert = get_peft_model(model.bert, lora_config)

    # 3. Resolve checkpoint path
    checkpoint_path = config.MODELS_DIR / config.CHECKPOINT_FILENAME
    adapters_path = config.MODELS_DIR / config.ADAPTERS_DIRNAME

    # 4. Auto-download from HF if missing or forced
    if not checkpoint_path.exists() or not adapters_path.exists() or force_download:
        print(f"Artifacts missing locally. Downloading from {config.HF_REPO_ID}...")
        try:
            # Download main checkpoint
            hf_hub_download(
                repo_id=config.HF_REPO_ID,
                filename=config.CHECKPOINT_FILENAME,
                local_dir=str(config.MODELS_DIR),
            )

            # Download LoRA adapters folder
            snapshot_download(
                repo_id=config.HF_REPO_ID,
                allow_patterns=[f"{config.ADAPTERS_DIRNAME}/*"],
                local_dir=str(config.MODELS_DIR),
            )
        except Exception as e:
            print(f"Error downloading from Hugging Face: {e}")
            raise FileNotFoundError(
                "Could not load required artifacts from HF Hub."
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


def load_onnx_model_and_tokenizer(
    repo_id: str = config.HF_REPO_ID,
    use_gpu: bool = False,
    force_download: bool = False,
) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Download and load ONNX model and tokenizer from HF Hub for inference.
    """
    if ort is None:
        print("[ERROR] onnxruntime not installed.")
        return None, None

    local_dir = config.ONNX_CACHE_DIR
    local_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download ONNX Model
    try:
        onnx_path = hf_hub_download(
            repo_id=repo_id,
            filename=config.ONNX_MODEL_FILENAME,
            local_dir=str(local_dir),
            repo_type="model",
            force_download=force_download,
        )
        # Optional data file download
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=config.ONNX_DATA_FILENAME,
                local_dir=str(local_dir),
                repo_type="model",
                force_download=force_download,
            )
        except Exception: # pylint: disable=broad-exception-caught
            pass  # Data file might not exist for smaller models
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[ERROR] Failed to download ONNX model: {e}")
        return None, None

    # 2. Download Tokenizer
    if Tokenizer is None:
        print("[ERROR] tokenizers package not installed.")
        tokenizer = None
    else:
        try:
            tokenizer_path = hf_hub_download(
                repo_id=repo_id,
                filename=f"{config.TOKENIZER_DIRNAME}/{config.TOKENIZER_FILENAME}",
                local_dir=str(local_dir),
                repo_type="model",
                force_download=force_download,
            )
            tokenizer = Tokenizer.from_file(tokenizer_path)
        except Exception as e: # pylint: disable=broad-exception-caught
            print(f"[ERROR] Failed to download/load tokenizer: {e}")
            tokenizer = None

    # 3. Create Session
    providers = (
        ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if use_gpu
        else ["CPUExecutionProvider"]
    )

    try:
        session = ort.InferenceSession(onnx_path, providers=providers)
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[ERROR] Failed to create ONNX session: {e}")
        return None, None

    return session, tokenizer
