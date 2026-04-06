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
- ONNX models (FP32 + quantized variants when present)
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


def main() -> None:
    """Main function to handle the model upload process."""
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
    hf_username = os.environ.get("HF_USERNAME")
    if not hf_username:
        hf_username = input("Enter HuggingFace Username (or set HF_USERNAME): ").strip()

    repo_id = config.HF_REPO_ID
    if hf_username not in repo_id:
        # Fallback if user wants to upload to their own fork/repo
        repo_id = f"{hf_username}/sentinelai-bert-filter"

    print(f"Target Repo: {repo_id}")

    # 3. Paths
    models_dir = config.MODELS_DIR
    logs_dir = config.LOGS_DIR

    # Artifacts to upload
    artifacts = [
        models_dir / config.ADAPTERS_DIRNAME,  # Folder
        models_dir / config.CHECKPOINT_FILENAME,  # File
        logs_dir / "training_log.json",  # File
        models_dir / "README.md",  # File (Model Card)
        models_dir / config.ONNX_MODEL_FILENAME,  # ONNX File
        models_dir / config.TOKENIZER_DIRNAME,  # Tokenizer Folder
    ]

    # Verify critical paths (ONNX/Tokenizer might not exist yet)
    for art in artifacts[:4]:
        if not art.exists():
            print(f"Error: Artifact not found: {art}")
            return

    # 4. Create Repo
    api = HfApi(token=hf_token)
    try:
        url = create_repo(repo_id, repo_type="model", token=hf_token, exist_ok=True, private=False)
        print(f"Repository ready: {url}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Repo creation failed: {e}")
        return

    # 5. Upload
    print("\nStarting upload...")

    try:
        # Upload LoRA Adapters (Folder)
        print("Uploading LoRA adapters...")
        api.upload_folder(
            folder_path=str(models_dir / config.ADAPTERS_DIRNAME),
            repo_id=repo_id,
            path_in_repo=config.ADAPTERS_DIRNAME,
            repo_type="model",
        )

        # Upload Full Checkpoint
        print(f"Uploading {config.CHECKPOINT_FILENAME}...")
        api.upload_file(
            path_or_fileobj=str(models_dir / config.CHECKPOINT_FILENAME),
            path_in_repo=config.CHECKPOINT_FILENAME,
            repo_id=repo_id,
            repo_type="model",
        )

        # Upload ONNX models if present (base + quantized variants)
        for onnx_filename in config.ONNX_VARIANT_MODEL_FILENAMES:
            onnx_path = models_dir / onnx_filename
            if not onnx_path.exists():
                continue

            print(f"Uploading ONNX model: {onnx_filename}...")
            api.upload_file(
                path_or_fileobj=str(onnx_path),
                path_in_repo=onnx_filename,
                repo_id=repo_id,
                repo_type="model",
            )

            # Upload ONNX external data file if exists
            data_path = onnx_path.with_suffix(".onnx.data")
            if data_path.exists():
                print(f"Uploading ONNX data file: {data_path.name}...")
                api.upload_file(
                    path_or_fileobj=str(data_path),
                    path_in_repo=data_path.name,
                    repo_id=repo_id,
                    repo_type="model",
                )

        # Upload Tokenizer Folder if exists
        tokenizer_dir = models_dir / config.TOKENIZER_DIRNAME
        if tokenizer_dir.exists():
            print("Uploading tokenizer folder...")
            api.upload_folder(
                folder_path=str(tokenizer_dir),
                path_in_repo=config.TOKENIZER_DIRNAME,
                repo_id=repo_id,
                repo_type="model",
            )

        # Upload Log
        print("Uploading training logs...")
        api.upload_file(
            path_or_fileobj=str(logs_dir / "training_log.json"),
            path_in_repo="training_log.json",
            repo_id=repo_id,
            repo_type="model",
        )

        # Upload README (Model Card) to root
        print("Uploading README.md (Model Card)...")
        api.upload_file(
            path_or_fileobj=str(models_dir / "README.md"),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="model",
        )

        print("\n" + "=" * 80)
        print(f"SUCCESS! Model hosted at: https://huggingface.co/{repo_id}")
        print("=" * 80)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\nUpload failed: {e}")


if __name__ == "__main__":
    main()
