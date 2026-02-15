"""
Binary Risk Evaluation for SentinelAI.
Converts multi-class (7-category) results into binary (Risk vs No-Risk) metrics.
Provides a side-by-side comparison between SentiBERT and the Keyword Baseline.
"""

import json
from pathlib import Path
from typing import Dict
import numpy as np

def calculate_binary_metrics(cm: np.ndarray) -> Dict:
    """
    Calculates binary classification metrics from a 7x7 confusion matrix.
    Risk categories: 2, 3, 4, 5, 6 (Stress, Burnout, Depression, Harassment, Suicidal)
    No-Risk categories: 0, 1 (Neutral, Humor)
    
    CM structure: cm[true][pred]
    """
    # Mapping indices
    no_risk_indices = [0, 1]
    risk_indices = [2, 3, 4, 5, 6]
    
    # Calculate components
    # True Negative: True No-Risk predicted as No-Risk
    tn = cm[np.ix_(no_risk_indices, no_risk_indices)].sum()
    
    # False Positive: True No-Risk predicted as Risk
    fp = cm[np.ix_(no_risk_indices, risk_indices)].sum()
    
    # False Negative: True Risk predicted as No-Risk
    fn = cm[np.ix_(risk_indices, no_risk_indices)].sum()
    
    # True Positive: True Risk predicted as Risk
    tp = cm[np.ix_(risk_indices, risk_indices)].sum()
    
    # Metrics calculation
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "confusion_matrix": [
            [int(tn), int(fp)],
            [int(fn), int(tp)]
        ],
        "metrics": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1)
        },
        "counts": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }

def main():
    print("=" * 80)
    print("SentinelAI Binary Risk Analysis")
    print("=" * 80)

    # Paths
    script_dir = Path(__file__).parent
    eval_dir = script_dir.parent / "evaluation"
    bert_path = eval_dir / "evaluation_results.json"
    baseline_path = eval_dir / "baseline_keyword_results.json"
    output_path = eval_dir / "binary_comparison_results.json"

    if not bert_path.exists() or not baseline_path.exists():
        print(f"Error: Required results files not found in {eval_dir}")
        return

    # Load results
    with open(bert_path, 'r', encoding='utf-8') as f:
        bert_data = json.load(f)
    
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)

    # Extract 7x7 confusion matrices
    bert_cm = np.array(bert_data["category_classification"]["confusion_matrix"])
    baseline_cm = np.array(baseline_data["category_classification"]["confusion_matrix"])

    # Calculate binary metrics
    bert_binary = calculate_binary_metrics(bert_cm)
    baseline_binary = calculate_binary_metrics(baseline_cm)

    # Side-by-side comparison
    comparison = {
        "sentibert": bert_binary,
        "keyword_baseline": baseline_binary,
        "analysis": {
            "accuracy_improvement": bert_binary["metrics"]["accuracy"] - baseline_binary["metrics"]["accuracy"],
            "recall_improvement": bert_binary["metrics"]["recall"] - baseline_binary["metrics"]["recall"],
            "description": "Binary classification: Risk (categories 2-6) vs No-Risk (0-1)"
        }
    }

    # Print Report
    print(f"{'Metric':<15} | {'Baseline':<12} | {'SentiBERT':<12}")
    print("-" * 45)
    for metric in ["accuracy", "precision", "recall", "f1_score"]:
        b_val = baseline_binary["metrics"][metric]
        s_val = bert_binary["metrics"][metric]
        print(f"{metric:<15} | {b_val:<12.4f} | {s_val:<12.4f}")

    print("\n" + "=" * 80)
    print("GATEKEEPER PERFORMANCE (RECALL IS KEY)")
    print("=" * 80)
    print(f"SentiBERT catches {bert_binary['metrics']['recall']*100:.1f}% of risks.")
    print(f"Keyword Baseline catches {baseline_binary['metrics']['recall']*100:.1f}% of risks.")
    print(f"SentiBERT is {bert_binary['counts']['false_negatives']} misses vs Baseline {baseline_binary['counts']['false_negatives']} misses.")

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"\nBinary comparison results saved to: {output_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
