"""
Script to upload the trained SentinelAI filter model to Hugging Face Hub.
This enables the inference service (FastAPI) to pull the model weights without
bloating the git repository with large binary files in the future.

REQUIREMENTS:
- pip install huggingface_hub
- Set HF_TOKEN environment variable (Write access token)

ARTIFACTS UPLOADED:
- lora_adapters/ (Config & Weights)
- dual_head_classifier.pt (Full checkpoint with heads)
- ONNX models (base FP32, FP16, dynamic INT8, static INT8)
- tokenizer/ (Tokenizer files for ONNX inference)
- Training logs and README/model card
"""

# pylint: disable=wrong-import-position

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config


def main():
    """Main function to handle the upload process."""
    print("=" * 80)
    print("SentinelAI HuggingFace Model Uploader")
    print("=" * 80)

    # 1. Credentials
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("Error: HF_TOKEN environment variable not set.")
        print("Please get a Write token from https://huggingface.co/settings/tokens")
        return

    # 2. Configuration
    # Prefer HF_MODEL from env, fallback to config
    repo_id = os.environ.get("HF_MODEL")
    if not repo_id:
        repo_id = config.HF_REPO_ID
        hf_username = os.environ.get("HF_USERNAME")
        if hf_username and hf_username not in repo_id:
            repo_id = f"{hf_username}/sentinelai-bert-filter"
    
    print(f"Target Repo: {repo_id}")

    # 3. Paths
    models_dir = config.MODELS_DIR

    # PyTorch artifacts
    pytorch_artifacts = [
        models_dir / config.ADAPTERS_DIRNAME,  # Folder
        models_dir / config.CHECKPOINT_FILENAME,  # File
        models_dir / "training_log.json",  # File
        models_dir / "README.md",  # File (Model Card)
    ]
    
    # ONNX artifacts (including .data files for large models)
    onnx_artifacts = [
        models_dir / "sentinelai_model.onnx",
        models_dir / "sentinelai_model_fp16.onnx",
        models_dir / "sentinelai_model_dynamic_int8.onnx",
        models_dir / "sentinelai_model_static_int8.onnx",
        models_dir / "tokenizer",
    ]
    
    # Check for .onnx.data companion files
    for onnx_file in list(onnx_artifacts):
        if onnx_file.suffix == ".onnx" and onnx_file.exists():
            data_file = Path(str(onnx_file) + ".data")
            if data_file.exists():
                onnx_artifacts.append(data_file)

    # Verify PyTorch paths
    missing_pytorch = [art for art in pytorch_artifacts if not art.exists()]
    if missing_pytorch:
        print(f"Warning: Some PyTorch artifacts not found:")
        for art in missing_pytorch:
            print(f"  - {art}")
    
    # Verify ONNX paths - track individually
    existing_onnx = [art for art in onnx_artifacts if art.exists()]
    missing_onnx = [art for art in onnx_artifacts if not art.exists()]
    
    if missing_onnx:
        print(f"Warning: Some ONNX artifacts not found:")
        for art in missing_onnx:
            print(f"  - {art}")
        print("\nNote: Run export_onnx.py and quantize_onnx.py first to generate ONNX models")
    
    # Determine what to upload
    upload_pytorch = len(missing_pytorch) == 0
    upload_onnx = len(existing_onnx) > 0  # Upload if ANY ONNX files exist
    
    if not upload_pytorch and not upload_onnx:
        print("\nError: No artifacts found to upload")
        return
    
    print(f"\nWill upload:")
    print(f"  - PyTorch models: {'Yes' if upload_pytorch else 'No (missing files)'}")
    print(f"  - ONNX models: {'Yes' if upload_onnx else 'No'} ({len(existing_onnx)}/{len(onnx_artifacts)} files available)")

    # 4. Create Repo
    api = HfApi(token=hf_token)
    try:
        url = create_repo(repo_id, token=hf_token, exist_ok=True, private=False)
        print(f"Repository ready: {url}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Repo creation failed: {e}")
        return

    # 5. Upload
    print("\nStarting upload...")

    try:
        # === PyTorch Models ===
        if upload_pytorch:
            print("\n--- Uploading PyTorch Models ---")
            
            # Upload LoRA Adapters (Folder)
            print("Uploading LoRA adapters...")
            api.upload_folder(
                folder_path=str(models_dir / "lora_adapters"),
                repo_id=repo_id,
                path_in_repo="lora_adapters",
            )

            # Upload Full Checkpoint
            print("Uploading dual_head_classifier.pt...")
            api.upload_file(
                path_or_fileobj=str(models_dir / "dual_head_classifier.pt"),
                path_in_repo="dual_head_classifier.pt",
                repo_id=repo_id,
            )

            # Upload Log
            print("Uploading training logs...")
            api.upload_file(
                path_or_fileobj=str(models_dir / "training_log.json"),
                path_in_repo="training_log.json",
                repo_id=repo_id,
            )

            # Upload README (Model Card) to root
            print("Uploading README.md (Model Card)...")
            api.upload_file(
                path_or_fileobj=str(models_dir / "README.md"),
                path_in_repo="README.md",
                repo_id=repo_id,
            )
        
        # === ONNX Models ===
        if upload_onnx:
            print("\n--- Uploading ONNX Models ---")
            
            # Helper function to upload ONNX model and its .data file if exists
            def upload_onnx_model(model_name):
                """Upload ONNX model and companion .data file if it exists."""
                model_path = models_dir / model_name
                if not model_path.exists():
                    print(f"Skipping {model_name} (not found)")
                    return False
                
                # Upload main model file
                print(f"Uploading {model_name}...")
                api.upload_file(
                    path_or_fileobj=str(model_path),
                    path_in_repo=model_name,
                    repo_id=repo_id,
                )
                
                # Upload .data file if exists
                data_path = Path(str(model_path) + ".data")
                if data_path.exists():
                    print(f"  Uploading {model_name}.data...")
                    api.upload_file(
                        path_or_fileobj=str(data_path),
                        path_in_repo=f"{model_name}.data",
                        repo_id=repo_id,
                    )
                return True
            
            # Upload all ONNX models that exist
            uploaded_count = 0
            uploaded_count += upload_onnx_model("sentinelai_model.onnx")
            uploaded_count += upload_onnx_model("sentinelai_model_fp16.onnx")
            uploaded_count += upload_onnx_model("sentinelai_model_dynamic_int8.onnx")
            uploaded_count += upload_onnx_model("sentinelai_model_static_int8.onnx")
            
            # Upload tokenizer folder if exists
            tokenizer_path = models_dir / "tokenizer"
            if tokenizer_path.exists():
                print("Uploading tokenizer...")
                api.upload_folder(
                    folder_path=str(tokenizer_path),
                    repo_id=repo_id,
                    path_in_repo="tokenizer",
                )
            else:
                print("Skipping tokenizer (not found)")

        print("\n" + "=" * 80)
        print(f"SUCCESS! Model hosted at: https://huggingface.co/{repo_id}")
        if upload_pytorch:
            print("✓ PyTorch models uploaded")
        if upload_onnx:
            print(f"✓ ONNX models uploaded ({uploaded_count} models + tokenizer)")
        print("=" * 80)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\nUpload failed: {e}")


if __name__ == "__main__":
    main()
