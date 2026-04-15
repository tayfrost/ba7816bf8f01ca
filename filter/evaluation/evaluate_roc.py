"""
ROC Curve Analysis and Threshold Tuning for SentiBERT.

Calculates the Receiver Operating Characteristic (ROC) curve for the binary
gatekeeping task. (Risk vs No-Risk)

Determines the optimal classification threshold to maximise safety recall
while maintaining reasonable precision.
"""

# pylint: disable=wrong-import-position

import json
import sys
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import auc, roc_curve

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import load_dataset, get_dataset_path
from services.model_factory import load_production_model


def get_binary_probabilities(
    model: torch.nn.Module, loader: torch.utils.data.DataLoader, device: torch.device
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get probability scores for the binary risk class (Risk = 1).
    Risk categories: 2, 3, 4, 5, 6
    No-Risk categories: 0, 1
    """
    model.eval()
    all_probs = []
    all_labels = []

    # Indices for Risk Categories in the 7-class output
    risk_indices = [
        config.CATEGORY_MAP[cat] for cat in config.RISK_CATEGORIES
    ]

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            category_labels = batch["category_label"].to(device)

            # Forward pass
            logits, _ = model(input_ids, attention_mask)
            probs = F.softmax(logits, dim=1)

            # Sum probabilities of all Risk classes to get P(Risk)
            risk_probs = probs[:, risk_indices].sum(dim=1)

            # Convert 7-class labels to Binary Risk labels (1 for Risk, 0 for No-Risk)
            binary_labels = torch.isin(
                category_labels, torch.tensor(risk_indices).to(device)
            ).long()

            all_probs.extend(risk_probs.cpu().numpy())
            all_labels.extend(binary_labels.cpu().numpy())

    return np.array(all_probs), np.array(all_labels)


def find_optimal_threshold(
    fpr: np.ndarray, tpr: np.ndarray, thresholds: np.ndarray
) -> float:
    """Find threshold that maximises J-statistic (TPR - FPR)."""
    j_scores = tpr - fpr
    best_idx = np.argmax(j_scores)
    return float(thresholds[best_idx])


def plot_roc_curve(fpr, tpr, roc_auc, output_path: Path):
    """Plot and save ROC curve."""
    plt.figure(figsize=(10, 8))
    plt.plot(
        fpr,
        tpr,
        color="darkorange",
        lw=2,
        label=f"ROC curve (AUC = {roc_auc:.4f})",
    )
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate (Recall)")
    plt.title("Receiver Operating Characteristic - Binary Risk Gatekeeper")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.savefig(output_path)
    plt.close()
    print(f"Saved ROC plot: {output_path}")


def main():
    """Main function to perform ROC analysis and threshold tuning."""
    print("=" * 80)
    print("SentinelAI ROC Analysis & Threshold Tuning")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Load Data (SSOT)
    print("Loading test dataset...")
    _, _, test_loader, _ = load_dataset(
        dataset_path=str(get_dataset_path("sentinelai_dataset_v0.2.json")),
        mix_datasets=True,
    )

    # 2. Load Model (SSOT)
    print("Loading production model...")
    model = load_production_model(device=device)

    # 3. Get Probabilities
    print("Running inference...")
    y_scores, y_true = get_binary_probabilities(model, test_loader, device)

    # 4. Calculate ROC
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    print(f"\nBinary ROC AUC: {roc_auc:.4f}")

    # 5. Optimal Thresholds
    # A. Maximise J-Statistic (Balanced)
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold = thresholds[optimal_idx]

    # B. Safety-Critical (Recall >= 0.99)
    safety_idx = np.where(tpr >= 0.99)[0][-1] # Last index where recall >= 0.99 (highest threshold)
    safety_threshold = thresholds[safety_idx]

    print("\nThreshold Analysis:")
    print(f"{'Strategy':<20} | {'Threshold':<10} | {'Recall':<10} | {'FPR':<10}")
    print("-" * 60)
    print(
        f"{'Balanced (J-Stat)':<20} | {optimal_threshold:<10.4f} | "
        f"{tpr[optimal_idx]:<10.4f} | {fpr[optimal_idx]:<10.4f}"
    )
    print(
        f"{'Safety (99% Recall)':<20} | {safety_threshold:<10.4f} | "
        f"{tpr[safety_idx]:<10.4f} | {fpr[safety_idx]:<10.4f}"
    )

    # 6. Save Artifacts
    plot_roc_curve(fpr, tpr, roc_auc, config.IMAGES_DIR / "roc_curve.png")

    results = {
        "roc_auc": float(roc_auc),
        "thresholds": {
            "balanced": {
                "value": float(optimal_threshold),
                "recall": float(tpr[optimal_idx]),
                "fpr": float(fpr[optimal_idx]),
            },
            "safety_critical": {
                "value": float(safety_threshold),
                "recall": float(tpr[safety_idx]),
                "fpr": float(fpr[safety_idx]),
            },
        },
    }

    results_path = config.RESULTS_DIR / "roc_evaluation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
