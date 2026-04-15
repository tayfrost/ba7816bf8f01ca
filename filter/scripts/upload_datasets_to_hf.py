"""
Script to upload the SentinelAI datasets to Hugging Face Hub.
This moves large JSON/CSV files out of the git repository and into a dedicated 
Hugging Face Dataset repository.

REQUIREMENTS:
- pip install huggingface_hub
- Set HF_TOKEN environment variable (Write access token)

ARTIFACTS UPLOADED:
- All .csv files in datasets/
- All .json files in datasets/
- README.md in datasets/
"""

# pylint: disable=wrong-import-position

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# Add parent directory to path to allow importing config
sys.path.append(str(Path(__file__).parent.parent))

import config


def main():
    """Main function to handle the dataset upload process."""
    print("=" * 80)
    print("SentinelAI HuggingFace Dataset Uploader")
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

    repo_id = config.HF_DATASETS_REPO_ID
    if hf_username not in repo_id:
        # Fallback if user wants to upload to their own fork/repo
        repo_id = f"{hf_username}/sentinelai-datasets"

    print(f"Target Dataset Repo: {repo_id}")

    # 3. Create Dataset Repo
    api = HfApi(token=hf_token)
    try:
        url = create_repo(repo_id, repo_type="dataset", token=hf_token, exist_ok=True, private=False)
        print(f"Repository ready: {url}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Repo creation failed: {e}")
        return

    # 4. Upload Files
    dataset_files = list(config.DATASETS_DIR.glob("*.json")) + list(config.DATASETS_DIR.glob("*.csv"))
    readme_path = config.DATASETS_DIR / "README.md"
    if readme_path.exists():
        dataset_files.append(readme_path)

    print(f"\nStarting upload of {len(dataset_files)} files...")

    try:
        for file_path in dataset_files:
            if not file_path.exists():
                continue

            print(f"Uploading {file_path.name}...")
            api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=file_path.name,
                repo_id=repo_id,
                repo_type="dataset",
            )

        print("\n" + "=" * 80)
        print(f"SUCCESS! Datasets hosted at: https://huggingface.co/datasets/{repo_id}")
        print("=" * 80)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\nUpload failed: {e}")


if __name__ == "__main__":
    main()
