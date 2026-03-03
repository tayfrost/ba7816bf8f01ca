"""
ONNX model factory for inference.

Separated from model_factory.py to avoid importing torch dependencies.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
from tqdm import tqdm

try:
    import onnxruntime as ort
except ImportError:
    ort = None

# Ensure internal imports work regardless of execution context
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

import config


def load_onnx_model_and_tokenizer(repo_id: str = None, use_gpu: bool = False):
    """
    Download and load ONNX model and tokenizer from HF Space for inference.
    
    Args:
        repo_id: HuggingFace model repo ID (uses HF_MODEL env var if None)
        use_gpu: Whether to use GPU for inference (requires onnxruntime-gpu)
    
    Returns:
        Tuple of (ONNX InferenceSession, tokenizer dict)
    """
    print("[INIT] Starting load_onnx_model_and_tokenizer...")
    
    if ort is None:
        raise ImportError("onnxruntime not installed. Run: pip install onnxruntime")
    
    print("[INIT] onnxruntime detected")
    
    if repo_id is None:
        repo_id = os.environ.get("HF_MODEL")
        if not repo_id:
            raise ValueError("repo_id not provided and HF_MODEL env var not set")
        print(f"[INIT] Using HF_MODEL from env: {repo_id}")
    else:
        print(f"[INIT] Using provided repo_id: {repo_id}")
    
    print(f"[DOWNLOAD] Downloading ONNX model from {repo_id}...")
    print("[DOWNLOAD] This may take a few minutes for large models (200-400MB)...")
    local_dir = config.MODELS_DIR / "onnx_cache"
    print(f"[DOWNLOAD] Cache directory: {local_dir}")
    local_dir.mkdir(parents=True, exist_ok=True)
    print(f"[DOWNLOAD] Cache directory ready")
    
    print(f"[DOWNLOAD] Fetching sentinelai_model.onnx...")
    onnx_path = hf_hub_download(
        repo_id=repo_id,
        filename="sentinelai_model.onnx",
        repo_type="model",
        local_dir=str(local_dir),
    )
    print(f"[DOWNLOAD] ✓ ONNX model downloaded to: {onnx_path}")
    
    # Download .data file if exists
    try:
        print("[DOWNLOAD] Checking for additional model data files...")
        hf_hub_download(
            repo_id=repo_id,
            filename="sentinelai_model.onnx.data",
            repo_type="model",
            local_dir=str(local_dir),
        )
        print(f"[DOWNLOAD] ✓ Model data file downloaded")
    except Exception as e:
        print(f"[DOWNLOAD] No .data file found (this is normal for some models)")
    
    # Download tokenizer files
    print(f"[DOWNLOAD] Fetching tokenizer from {repo_id}...")
    
    tokenizer_path = hf_hub_download(
        repo_id=repo_id,
        filename="tokenizer/tokenizer.json",
        repo_type="model",
        local_dir=str(local_dir),
    )
    print(f"[DOWNLOAD] ✓ Tokenizer downloaded to: {tokenizer_path}")
    
    print(f"[LOAD] Loading tokenizer from file...")
    tokenizer = Tokenizer.from_file(tokenizer_path)
    print(f"[LOAD] ✓ Tokenizer loaded successfully")
    
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu else ["CPUExecutionProvider"]
    print(f"[LOAD] Creating ONNX runtime session...")
    print(f"[LOAD] Using providers: {providers}")
    print(f"[LOAD] Model path: {onnx_path}")
    
    session = ort.InferenceSession(onnx_path, providers=providers)
    
    print(f"[LOAD] ✓ ONNX InferenceSession created successfully")
    print(f"[LOAD] ✓ Model and tokenizer ready for inference")
    return session, tokenizer


# Backwards compatibility alias
def load_model_for_inference(repo_id: str = None, use_gpu: bool = False):
    """
    Backwards compatibility wrapper for load_onnx_model_and_tokenizer.
    Returns only the session (old behavior).
    """
    session, _ = load_onnx_model_and_tokenizer(repo_id, use_gpu)
    return session
