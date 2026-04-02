"""
Evaluation script for trained dual-head BERT classifier.
Generates confusion matrices, per-class metrics, and visualisations.
"""

# pylint: disable=wrong-import-position

import json
import sys
from pathlib import Path
from typing import Dict, Sized, TypedDict, cast  # pylint: disable=deprecated-class

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from torch.utils.data import DataLoader

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import load_dataset
from services.model_factory import load_production_model


def plot_confusion_matrix(
    cm: np.ndarray, labels: list, title: str, output_path: Path, figsize=(10, 8)
):
    """
    Plot and save confusion matrix as heatmap.

    Args:
        cm: Confusion matrix array
        labels: Class labels
        title: Plot title
        output_path: Path to save PNG
        figsize: Figure size tuple
    """
    plt.figure(figsize=figsize)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        cbar_kws={"label": "Count"},
    )
    plt.title(title, fontsize=16, pad=20)
    plt.ylabel("True Label", fontsize=12)
    plt.xlabel("Predicted Label", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved confusion matrix: {output_path}")


def evaluate_model(
    model: nn.Module, test_loader: DataLoader, device: torch.device
) -> dict:
    """
    Evaluate model on test set and return predictions + labels.

    Args:
        model: Trained dual-head classifier
        test_loader: Test data loader
        device: Computation device

    Returns:
        Dictionary with predictions, labels, and metrics
    """
    model.eval()

    all_category_preds = []
    all_category_labels = []
    all_severity_preds = []
    all_severity_labels = []

    category_criterion = nn.CrossEntropyLoss()
    severity_criterion = nn.CrossEntropyLoss()

    total_loss = 0.0

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            category_labels = batch["category_label"].to(device)
            severity_labels = batch["severity_label"].to(device)

            # Forward pass
            category_logits, severity_logits = model(input_ids, attention_mask)

            # Calculate loss
            loss_category = category_criterion(category_logits, category_labels)
            loss_severity = severity_criterion(severity_logits, severity_labels)
            total_loss += (loss_category + loss_severity).item()

            # Get predictions
            _, category_preds = torch.max(category_logits, 1)
            _, severity_preds = torch.max(severity_logits, 1)

            # Store results
            all_category_preds.extend(category_preds.cpu().numpy())
            all_category_labels.extend(category_labels.cpu().numpy())
            all_severity_preds.extend(severity_preds.cpu().numpy())
            all_severity_labels.extend(severity_labels.cpu().numpy())

    avg_loss = total_loss / len(test_loader)

    return {
        "category_preds": np.array(all_category_preds),
        "category_labels": np.array(all_category_labels),
        "severity_preds": np.array(all_severity_preds),
        "severity_labels": np.array(all_severity_labels),
        "test_loss": avg_loss,
    }


# TypedDicts for clearer static typing (no runtime change)
class PerClassMetrics(TypedDict):
    """ "Metrics for a single class."""

    precision: float
    recall: float
    f1_score: float
    support: int


class ClassificationMetrics(TypedDict):
    """Overall and per-class metrics for classification."""

    accuracy: float
    per_class: Dict[str, PerClassMetrics]
    macro_avg: Dict[str, float]
    weighted_avg: Dict[str, float]


def calculate_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, labels: list
) -> ClassificationMetrics:  # pylint: disable=line-too-long
    """
    Calculate per-class and overall metrics.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        labels: List of class names

    Returns:
        Dictionary with metrics
    """
    # Per-class metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(len(labels))), zero_division=0
    )

    # ensure indexable numpy arrays for static type-checkers (no runtime change)
    precision = np.asarray(precision)
    recall = np.asarray(recall)
    f1 = np.asarray(f1)
    support = np.asarray(support)

    # Overall accuracy
    accuracy = np.mean(y_true == y_pred)

    # Build per-class results
    per_class = {}
    for i, label in enumerate(labels):
        per_class[label] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1_score": float(f1[i]),
            "support": int(support[i]),
        }

    # Macro averages
    macro_avg = {
        "precision": float(np.mean(precision)),
        "recall": float(np.mean(recall)),
        "f1_score": float(np.mean(f1)),
    }

    # Weighted averages
    weighted_avg = {
        "precision": float(np.average(precision, weights=support)),
        "recall": float(np.average(recall, weights=support)),
        "f1_score": float(np.average(f1, weights=support)),
    }

    return {
        "accuracy": float(accuracy),
        "per_class": per_class,
        "macro_avg": macro_avg,
        "weighted_avg": weighted_avg,
    }


def main():
    """Main evaluation function."""
    print("=" * 80)
    print("SentinelAI BERT Filter Evaluation")
    print("=" * 80)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}\n")

    # Paths
    output_dir = config.EVAL_DIR
    output_dir.mkdir(exist_ok=True)

    # Load dataset
    print("Loading test dataset...")
    dataset_path = config.DATASETS_DIR / "sentinelai_dataset_v0.2.json"
    _, _, test_loader, _ = load_dataset(
        dataset_path=str(dataset_path),
        mix_datasets=True,  # Use same 7k mixed dataset as training
    )
    print(f"Test set: {len(cast(Sized, test_loader.dataset))} examples\n")

    # Load production model
    model = load_production_model(device=device)

    # Evaluate
    print("\nRunning evaluation...")
    results = evaluate_model(model, test_loader, device)
    print(f"Test Loss: {results['test_loss']:.4f}\n")

    # Category labels
    category_labels = [
        "neutral",
        "humor_sarcasm",
        "stress",
        "burnout",
        "depression",
        "harassment",
        "suicidal_ideation",
    ]

    # Severity labels
    severity_labels = ["none", "early", "middle", "late"]

    # Calculate metrics
    print("Calculating metrics...")
    category_metrics: ClassificationMetrics = calculate_metrics(
        results["category_labels"], results["category_preds"], category_labels
    )

    severity_metrics: ClassificationMetrics = calculate_metrics(
        results["severity_labels"], results["severity_preds"], severity_labels
    )

    # Print results
    print("\n" + "=" * 80)
    print("CATEGORY CLASSIFICATION RESULTS")
    print("=" * 80)
    print(f"Accuracy: {category_metrics['accuracy']:.4f}")
    print(f"Macro F1: {category_metrics['macro_avg']['f1_score']:.4f}")
    print(f"Weighted F1: {category_metrics['weighted_avg']['f1_score']:.4f}\n")

    print("Per-Class Metrics:")
    print(
        f"{'Class':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}"
    )
    print("-" * 80)
    for label, metrics in category_metrics["per_class"].items():
        print(
            f"{label:<20} {metrics['precision']:<12.4f} {metrics['recall']:<12.4f} "
            f"{metrics['f1_score']:<12.4f} {metrics['support']:<10}"
        )

    print("\n" + "=" * 80)
    print("SEVERITY CLASSIFICATION RESULTS")
    print("=" * 80)
    print(f"Accuracy: {severity_metrics['accuracy']:.4f}")
    print(f"Macro F1: {severity_metrics['macro_avg']['f1_score']:.4f}")
    print(f"Weighted F1: {severity_metrics['weighted_avg']['f1_score']:.4f}\n")

    print("Per-Class Metrics:")
    print(
        f"{'Stage':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}"
    )
    print("-" * 80)
    for label, metrics in severity_metrics["per_class"].items():
        print(
            f"{label:<20} {metrics['precision']:<12.4f} {metrics['recall']:<12.4f} "
            f"{metrics['f1_score']:<12.4f} {metrics['support']:<10}"
        )

    # Generate confusion matrices
    print("\n" + "=" * 80)
    print("Generating visualisations...")
    print("=" * 80)

    # Category confusion matrix
    category_cm = confusion_matrix(
        results["category_labels"], results["category_preds"]
    )
    plot_confusion_matrix(
        category_cm,
        category_labels,
        "Category Classification Confusion Matrix",
        output_dir / "confusion_matrix_category.png",
        figsize=(12, 10),
    )

    # Severity confusion matrix
    severity_cm = confusion_matrix(
        results["severity_labels"], results["severity_preds"]
    )
    plot_confusion_matrix(
        severity_cm,
        severity_labels,
        "Severity Classification Confusion Matrix",
        output_dir / "confusion_matrix_severity.png",
        figsize=(8, 6),
    )

    # Save results to JSON
    evaluation_results = {
        "test_loss": results["test_loss"],
        "category_classification": {
            "accuracy": category_metrics["accuracy"],
            "macro_avg": category_metrics["macro_avg"],
            "weighted_avg": category_metrics["weighted_avg"],
            "per_class": category_metrics["per_class"],
            "confusion_matrix": category_cm.tolist(),
        },
        "severity_classification": {
            "accuracy": severity_metrics["accuracy"],
            "macro_avg": severity_metrics["macro_avg"],
            "weighted_avg": severity_metrics["weighted_avg"],
            "per_class": severity_metrics["per_class"],
            "confusion_matrix": severity_cm.tolist(),
        },
    }

    results_path = output_dir / "evaluation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_results, f, indent=2)
    print(f"\nEvaluation results saved to: {results_path}")

    print("\n" + "=" * 80)
    print("Evaluation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
