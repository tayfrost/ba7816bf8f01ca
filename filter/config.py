"""
Configuration constants for the SentinelAI filter service.
Serves as the SSOT for model parameters and paths.
"""

import os
from pathlib import Path

# Project Structure
FILTER_DIR = Path(__file__).parent
PROJECT_ROOT = FILTER_DIR.parent
MODELS_DIR = FILTER_DIR / "models"
LOGS_DIR = MODELS_DIR / "logs"
EVAL_DIR = FILTER_DIR / "evaluation"
RESULTS_DIR = EVAL_DIR / "results"
IMAGES_DIR = RESULTS_DIR / "images"
NOTEBOOKS_DIR = FILTER_DIR / "notebooks"
NOTEBOOK_RESULTS_DIR = NOTEBOOKS_DIR / "results"
NOTEBOOK_IMAGES_DIR = NOTEBOOK_RESULTS_DIR / "images"
DATASETS_DIR = PROJECT_ROOT / "datasets"

# Model Configuration
MODEL_NAME = "bert-base-uncased"

# Category to index mapping
CATEGORY_MAP = {
    "neutral": 0,
    "humor_sarcasm": 1,
    "stress": 2,
    "burnout": 3,
    "depression": 4,
    "harassment": 5,
    "suicidal_ideation": 6,
}

# Severity stage to index mapping
SEVERITY_MAP = {"none": 0, "early": 1, "middle": 2, "late": 3}

# Risk categories (for binary routing logic)
RISK_CATEGORIES = {"stress", "burnout", "depression", "harassment", "suicidal_ideation"}

NUM_CATEGORY_CLASSES = len(CATEGORY_MAP)
NUM_SEVERITY_CLASSES = len(SEVERITY_MAP)

# LoRA Configuration
LORA_R = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0.1
LORA_TARGET_MODULES = ["query", "value"]

# Hugging Face Configuration
HF_REPO_ID = "OguzhanKOG/sentinelai-bert-filter"
HF_DATASETS_REPO_ID = "OguzhanKOG/sentinelai-datasets"
CHECKPOINT_FILENAME = "dual_head_classifier.pt"
ADAPTERS_DIRNAME = "lora_adapters"

# ONNX Configuration
ONNX_MODEL_FILENAME = "sentinelai_model.onnx"
ONNX_DATA_FILENAME = "sentinelai_model.onnx.data"
ONNX_FP16_MODEL_FILENAME = "sentinelai_model_fp16.onnx"
ONNX_DYNAMIC_INT8_MODEL_FILENAME = "sentinelai_model_dynamic_int8.onnx"
ONNX_STATIC_INT8_MODEL_FILENAME = "sentinelai_model_static_int8.onnx"
ONNX_VARIANT_MODEL_FILENAMES = [
    ONNX_MODEL_FILENAME,
    ONNX_FP16_MODEL_FILENAME,
    ONNX_DYNAMIC_INT8_MODEL_FILENAME,
    ONNX_STATIC_INT8_MODEL_FILENAME,
]
TOKENIZER_DIRNAME = "tokenizer"
TOKENIZER_FILENAME = "tokenizer.json"
ONNX_CACHE_DIR = MODELS_DIR / "onnx_cache"

# Training Hyperparameters (Defaults)
BATCH_SIZE = 16
LEARNING_RATE = 3e-4
NUM_EPOCHS = 3
MAX_LENGTH = 128
SEED = 42

# Dataset-specific parameters
DATASET_SEED = 42

# WandB Configuration
WANDB_PROJECT = "sentinelai-filter"
USE_WANDB = os.environ.get("USE_WANDB", "False").lower() == "true"
