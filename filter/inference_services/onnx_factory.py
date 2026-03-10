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


def load_onnx_model_and_tokenizer(
    repo_id: str = None,
    model_name: str = "sentinelai_model.onnx",
    use_gpu: bool = False
):
    """
    Download and load ONNX model and tokenizer from HF Space for inference.
    
    Args:
        repo_id: HuggingFace model repo ID (uses HF_MODEL env var if None)
        model_name: Name of ONNX model file to load (default: sentinelai_model.onnx)
                   Options: sentinelai_model.onnx (FP32), sentinelai_model_fp16.onnx,
                           sentinelai_model_dynamic_int8.onnx, sentinelai_model_static_int8.onnx
        use_gpu: Whether to use GPU for inference (requires onnxruntime-gpu)
    
    Returns:
        Tuple of (ONNX InferenceSession, tokenizer dict)
    """
    print(f"[INIT] Starting load_onnx_model_and_tokenizer (model: {model_name})...")
    
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
    
    print(f"[DOWNLOAD] Fetching {model_name}...")
    onnx_path = hf_hub_download(
        repo_id=repo_id,
        filename=model_name,
        repo_type="model",
        local_dir=str(local_dir),
    )
    print(f"[DOWNLOAD] ✓ ONNX model downloaded to: {onnx_path}")
    
    # Download .data file if exists
    try:
        print("[DOWNLOAD] Checking for additional model data files...")
        data_filename = f"{model_name}.data"
        hf_hub_download(
            repo_id=repo_id,
            filename=data_filename,
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
    session, _ = load_onnx_model_and_tokenizer(repo_id, use_gpu=use_gpu)
    return session


def load_onnx_models_and_tokenizer(repo_id: str = None, use_gpu: bool = False):
    """
    Download and load all ONNX model variants and tokenizer from HF Space.
    
    Loads all quantized versions: FP32 (base), FP16, Dynamic INT8, Static INT8.
    Uses a shared tokenizer for all models.
    
    Args:
        repo_id: HuggingFace model repo ID (uses HF_MODEL env var if None)
        use_gpu: Whether to use GPU for inference (requires onnxruntime-gpu)
    
    Returns:
        Tuple of (models_dict, tokenizer) where models_dict contains:
            {
                "fp32": InferenceSession,
                "fp16": InferenceSession,
                "dynamic_int8": InferenceSession,
                "static_int8": InferenceSession
            }
    """
    print("="*80)
    print("[INIT] Loading all ONNX model variants...")
    print("="*80)
    
    if ort is None:
        raise ImportError("onnxruntime not installed. Run: pip install onnxruntime")
    
    if repo_id is None:
        repo_id = os.environ.get("HF_MODEL")
        if not repo_id:
            raise ValueError("repo_id not provided and HF_MODEL env var not set")
    
    print(f"[INIT] Repository: {repo_id}")
    print(f"[INIT] GPU: {'Enabled' if use_gpu else 'Disabled'}")
    
    # Model variants to load
    model_variants = {
        "fp32": "sentinelai_model.onnx",
        "fp16": "sentinelai_model_fp16.onnx",
        "dynamic_int8": "sentinelai_model_dynamic_int8.onnx",
        "static_int8": "sentinelai_model_static_int8.onnx",
    }
    
    models = {}
    tokenizer = None
    
    # Load each model variant
    for variant_name, model_filename in model_variants.items():
        print(f"\n[LOAD] Loading {variant_name.upper()} model...")
        try:
            session, tok = load_onnx_model_and_tokenizer(
                repo_id=repo_id,
                model_name=model_filename,
                use_gpu=use_gpu
            )
            models[variant_name] = session
            
            # Store tokenizer from first successful load
            if tokenizer is None:
                tokenizer = tok
            
            print(f"[LOAD] ✓ {variant_name.upper()} model loaded successfully")
            
        except Exception as e:
            print(f"[LOAD] ✗ Failed to load {variant_name.upper()}: {e}")
            print(f"[LOAD] Continuing with other models...")
    
    if len(models) == 0:
        raise RuntimeError("Failed to load any ONNX models")
    
    if tokenizer is None:
        raise RuntimeError("Failed to load tokenizer")
    
    print("\n" + "="*80)
    print(f"[INIT] ✓ Loaded {len(models)}/{len(model_variants)} model variants")
    print(f"[INIT] Available models: {', '.join(models.keys())}")
    print("="*80)
    
    return models, tokenizer
