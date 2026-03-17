"""
Keyword-based baseline classifier for mental health risk detection.
Uses regex patterns based on clinical criteria (MBI, DSM-5) to classify messages.
This serves as one of many comparison baselines for the BERT dual-head model.
"""

# pylint: disable=wrong-import-position

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, cast

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import (
    CATEGORY_MAP,
    get_dataset_path,
)

# Medically grounded keywords by category based on MBI, DSM-5, and clinical expertise.
# 0: neutral, 1: humor_sarcasm, 2: stress, 3: burnout,
# 4: depression, 5: harassment, 6: suicidal_ideation
KEYWORDS = {
    6: [
        "kill myself",
        "end it all",
        "suicide",
        "suicidal",
        "farewell",
        "better off dead",
        "no reason to live",
        "done with life",
    ],
    5: [
        "idiot",
        "stupid",
        "fire you",
        "shut up",
        "hate you",
        "worthless",
        "useless",
        "incompetent",
        "harass",
        "abuse",
        "toxic",
    ],
    4: [
        "hopeless",
        "empty",
        "worthless",
        "sad",
        "depressed",
        "depression",
        "no joy",
        "unhappy",
        "miserable",
        "crying",
    ],
    3: [
        "exhausted",
        "burnt out",
        "burnout",
        "cynical",
        "no point",
        "overwhelmed",
        "drained",
        "can't do this",
        "finished",
    ],
    2: [
        "stress",
        "stressed",
        "pressure",
        "deadline",
        "busy",
        "too much",
        "anxious",
        "anxiety",
        "worried",
        "overload",
    ],
    1: [
        "lol",
        "haha",
        "jk",
        "just kidding",
        "sarcasm",
        "sarcastic",
        "lmao",
        "rofl",
        "joke",
        "funny",
    ],
}

# Build regex patterns from the keyword lists (keeps individual source lines short)
KEYWORD_PATTERNS = {
    k: r"\b(" + "|".join(map(re.escape, v)) + r")\b" for k, v in KEYWORDS.items()
}


def classify_message(text: str) -> int:
    """
    Classifies a message based on keyword matching.
    Priority is given to higher-risk categories (Suicidal > Harassment > Depression > etc.)
    """
    text = text.lower()

    # Check patterns in order of priority (Risk categories first)
    for category in [6, 5, 4, 3, 2, 1]:
        if re.search(KEYWORD_PATTERNS[category], text):
            return category

    return 0  # Default to Neutral


def main():
    """Main function to evaluate the keyword baseline on the test set."""
    print("=" * 80)
    print("SentiBERT Keyword Baseline Evaluation")
    print("=" * 80)

    # Paths
    dataset_path = get_dataset_path("sentinelai_dataset_v0.2.json")
    output_dir = config.RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use raw text instead of tokenised tensors.
    with open(dataset_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    v01_path = get_dataset_path("sentinelai_dataset_v0.1.json")
    with open(v01_path, "r", encoding="utf-8") as f:
        data_v01 = json.load(f)

    # Reproduce the exact mixed dataset used in training/eval, 2000 pair injection
    torch.manual_seed(config.SEED)
    v02_indices = torch.randperm(len(full_data))[:2000].tolist()
    mixed_data = data_v01.copy()
    mixed_data.extend([full_data[i] for i in v02_indices])

    # Reproduce the shuffle and split from eval
    torch.manual_seed(config.DATASET_SEED)
    indices = torch.randperm(len(mixed_data)).tolist()
    shuffled_data = [mixed_data[i] for i in indices]

    # Take the test split
    test_start = int(len(shuffled_data) * 0.9)
    test_data = shuffled_data[test_start:]

    print(f"Processing {len(test_data)} test samples...")

    y_pred = []
    y_true = []

    # Reverse CATEGORY_MAP for metrics
    inv_category_map = {v: k for k, v in CATEGORY_MAP.items()}

    for item in test_data:
        message = item["message"]
        if "timestamp" in item and item["timestamp"]:
            message = f"[{item['timestamp']}] {message}"

        true_label_str = item["category"]
        true_label = CATEGORY_MAP[true_label_str]

        pred_label = classify_message(message)

        y_true.append(true_label)
        y_pred.append(pred_label)

    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    report = cast(
        Dict[str, Any],
        classification_report(
            y_true,
            y_pred,
            target_names=[inv_category_map[i] for i in range(7)],
            output_dict=True,
            zero_division=0,
        ),
    )

    # Calculate macro/weighted averages manually to match evaluate_model structure
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(7)), zero_division=0
    )

    macro_avg = {
        "precision": float(np.mean(precision)),
        "recall": float(np.mean(recall)),
        "f1_score": float(np.mean(f1)),
    }

    print("\n" + "=" * 80)
    print("KEYWORD BASELINE RESULTS")
    print("=" * 80)
    print(f"Overall Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_avg['f1_score']:.4f}\n")
    print("Per-Class Metrics:")
    print(f"{'Category':<20} {'Precision':<10} {'Recall':<10} {'F1-Score':<10}")
    print("-" * 55)

    per_class_results = {}
    for i in range(7):
        cat = inv_category_map[i]
        metrics: Dict[str, Any] = report[cat]
        per_class_results[cat] = {
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "f1_score": float(metrics["f1-score"]),
            "support": int(metrics["support"]),
        }
        prec = float(metrics["precision"])
        rec = float(metrics["recall"])
        f1s = float(metrics["f1-score"])
        print(f"{cat:<20} {prec:<10.4f} {rec:<10.4f} {f1s:<10.4f}")

    # Save results in a structure similar to evaluate_model.py
    results = {
        "category_classification": {
            "accuracy": float(accuracy),
            "macro_avg": macro_avg,
            "per_class": per_class_results,
            "confusion_matrix": cm.tolist(),
        }
    }

    output_path = output_dir / "baseline_keyword_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
