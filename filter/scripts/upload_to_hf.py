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
- Training logs and README/model card
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo

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
    hf_username = os.environ.get("HF_USERNAME")
    if not hf_username:
        hf_username = input("Enter HuggingFace Username (or set HF_USERNAME): ").strip()

    repo_name = "sentinelai-bert-filter"
    repo_id = f"{hf_username}/{repo_name}"

    print(f"Target Repo: {repo_id}")

    # 3. Paths
    script_dir = Path(__file__).parent
    models_dir = script_dir.parent / "models"

    # Artifacts to upload
    artifacts = [
        models_dir / "lora_adapters", # Folder
        models_dir / "dual_head_classifier.pt", # File
        models_dir / "training_log.json", # File
        models_dir / "README.md", # File (Model Card)
    ]

    # Verify paths
    for art in artifacts:
        if not art.exists():
            print(f"Error: Artifact not found: {art}")
            return

    # 4. Create Repo
    api = HfApi(token=hf_token)
    try:
        url = create_repo(repo_id, token=hf_token, exist_ok=True, private=False)
        print(f"Repository ready: {url}")
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"Repo creation failed: {e}")
        return

    # 5. Upload
    print("\nStarting upload...")

    try:
        # Upload LoRA Adapters (Folder)
        print("Uploading LoRA adapters...")
        api.upload_folder(
            folder_path=str(models_dir / "lora_adapters"),
            repo_id=repo_id,
            path_in_repo="lora_adapters"
        )

        # Upload Full Checkpoint
        print("Uploading dual_head_classifier.pt...")
        api.upload_file(
            path_or_fileobj=str(models_dir / "dual_head_classifier.pt"),
            path_in_repo="dual_head_classifier.pt",
            repo_id=repo_id
        )

        # Upload Log
        print("Uploading training logs...")
        api.upload_file(
            path_or_fileobj=str(models_dir / "training_log.json"),
            path_in_repo="training_log.json",
            repo_id=repo_id
        )

        # Upload README (Model Card) to root
        print("Uploading README.md (Model Card)...")
        api.upload_file(
            path_or_fileobj=str(models_dir / "README.md"),
            path_in_repo="README.md",
            repo_id=repo_id
        )

        print("\n" + "=" * 80)
        print(f"SUCCESS! Model hosted at: https://huggingface.co/{repo_id}")
        print("=" * 80)

    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"\nUpload failed: {e}")

if __name__ == "__main__":
    main()
