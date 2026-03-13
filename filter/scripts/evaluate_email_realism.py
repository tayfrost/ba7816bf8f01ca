"""
Email Realism Evaluation for SentinelAI.

Evaluates the trained SentiBERT model on the v0.3 "Email-Format" dataset.
This serves as an Out-of-Distribution (OOD) validation check to ensure/prove the model
can handle longer, more formal workplace communications despite being trained
primarily on Slack-style messages.

Focuses on:
- Accuracy on long-form text (20+ tokens).
- Robustness to different document structures (Subject lines, signatures).
- Generalisation capability.
"""

# pylint: disable=wrong-import-position

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import (
    MentalHealthDataset,
    CATEGORY_MAP,
    get_dataset_path,
)
from services.model_factory import load_production_model


def load_email_dataset(tokenizer, max_length: int = 128) -> DataLoader:
    """
    Loads specific email samples (ID > 5000) from v0.3 dataset.
    Does NOT mix with training data. Pure validation set.
    """
    v03_path = get_dataset_path("sentinelai_dataset_v0.3.json")

    with open(v03_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    # Filter for emails only (ID > 5000)
    email_data = [item for item in full_data if item['id'] > 5000]

    print(f"Loaded {len(email_data)} email samples for OOD validation.")

    dataset = MentalHealthDataset(email_data, tokenizer, max_length)
    loader = DataLoader(dataset, batch_size=config.BATCH_SIZE, shuffle=False)

    return loader

def evaluate_emails(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device
) -> Dict:
    """Run inference on the email dataset."""
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["category_label"].to(device)

            logits, _ = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    return {
        "preds": np.array(all_preds),
        "labels": np.array(all_labels)
    }

def main():
    """Main function to evaluate email realism."""
    print("=" * 80)
    print("SentinelAI Email Realism Evaluation (OOD Check)")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Loading production model...")
    model = load_production_model(device=device)

    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    loader = load_email_dataset(tokenizer)

    print("Running inference on emails...")
    results = evaluate_emails(model, loader, device)

    y_true = results["labels"]
    y_pred = results["preds"]

    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(
        y_true,
        y_pred,
        target_names=list(CATEGORY_MAP.keys()),
        output_dict=True,
        zero_division=0
    )

    print("\n" + "=" * 80)
    print("EMAIL REALISM RESULTS")
    print("=" * 80)
    print(f"Overall Accuracy: {accuracy:.4f}")

    output = {
        "accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "notes": "Evaluation on v0.3 email subset (IDs > 5000). OOD Check."
    }

    output_path = config.EVAL_DIR / "email_realism_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    main()
