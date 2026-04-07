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

def resolve_onnx_variant_filename(onnx_variant: str) -> str:
    """Resolve ONNX variant key to artifact filename.

    Supports canonical variant keys and direct `.onnx` filenames.
    """
    variant = (onnx_variant or "fp32").strip().lower()
    variant_map = {
        "fp32": config.ONNX_MODEL_FILENAME,
        "base": config.ONNX_MODEL_FILENAME,
        "default": config.ONNX_MODEL_FILENAME,
        "fp16": config.ONNX_FP16_MODEL_FILENAME,
        "dynamic_int8": config.ONNX_DYNAMIC_INT8_MODEL_FILENAME,
        "dynamic-int8": config.ONNX_DYNAMIC_INT8_MODEL_FILENAME,
    }

    if variant in variant_map:
        return variant_map[variant]

    if onnx_variant.endswith(".onnx"):
        return onnx_variant

    valid = ", ".join(sorted(set(variant_map.keys())))
    raise ValueError(
        f"Unsupported ONNX variant '{onnx_variant}'. "
        f"Use one of: {valid}, or provide a '.onnx' filename."
    )


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
    import types
    from peft import get_peft_model

    # Compatibility shim for certain torch builds (notably some Windows wheels)
    # where `torch.distributed` exists but `torch.distributed.tensor` is absent.
    # Newer PEFT versions may probe `torch.distributed.tensor.DTensor`.
    if hasattr(torch, "distributed") and not hasattr(torch.distributed, "tensor"):
        torch.distributed.tensor = types.SimpleNamespace(DTensor=type("_DummyDTensor", (), {}))

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
    onnx_variant: str = "fp32",
    fallback_to_base: bool = True,
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

    # 1. Resolve ONNX model filename from requested variant
    try:
        selected_filename = resolve_onnx_variant_filename(onnx_variant)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return None, None

    def _download_onnx_artifacts(filename: str) -> Optional[str]:
        onnx_file_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(local_dir),
            repo_type="model",
            force_download=force_download,
        )

        # Optional external data file download (large-model storage format)
        data_filename = Path(filename).with_suffix(".onnx.data").name
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=data_filename,
                local_dir=str(local_dir),
                repo_type="model",
                force_download=force_download,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return onnx_file_path

    try:
        print(f"[INFO] Loading ONNX variant: {selected_filename}")
        onnx_path = _download_onnx_artifacts(selected_filename)
    except Exception as e:  # pylint: disable=broad-exception-caught
        if fallback_to_base and selected_filename != config.ONNX_MODEL_FILENAME:
            print(
                f"[WARN] Failed to download variant '{selected_filename}': {e}. "
                f"Falling back to base model '{config.ONNX_MODEL_FILENAME}'."
            )
            try:
                onnx_path = _download_onnx_artifacts(config.ONNX_MODEL_FILENAME)
            except Exception as base_e:  # pylint: disable=broad-exception-caught
                print(f"[ERROR] Failed to download base ONNX model: {base_e}")
                return None, None
        else:
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
