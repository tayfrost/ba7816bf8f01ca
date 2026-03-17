"""
Gemini Flash Baseline Classifier for Mental Health Risk Detection.

Uses Google's Gemini 2.5 Flash Lite model to zero-shot classify workplace messages.

This serves as a high-performance baseline to compare SentiBERT's accuracy and
cost-efficiency against.

REQUIREMENTS:
- pip install google-genai
- Set GEMINI_API_KEY environment variable

METHODOLOGY:
- Uses the exact same 700-sample test set (split seed=config.DATASET_SEED)
  as BERT and Keyword baselines.
- Zero-shot prompting with strict category constraints.
- Reproduces the exact JSON output format for direct comparison.
"""

# pylint: disable=wrong-import-position

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, cast

import numpy as np
import torch

# Google GenAI SDK
from google import genai
from google.genai import types
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import CATEGORY_MAP, get_dataset_path

# Valid categories for prompting
VALID_CATEGORIES = list(CATEGORY_MAP.keys())


def classify_message_with_gemini(client: genai.Client, text: str) -> str:
    """
    Sends a message to Gemini 2.5 Flash Lite for zero-shot classification.
    Returns the predicted category string. Includes retry logic.
    """
    prompt = f"""
    You are an expert mental health classifier for workplace communications.
    Classify the following message into exactly one of these categories:
    {", ".join(VALID_CATEGORIES)}

    Message: "{text}"

    Return ONLY the category name. Do not add any explanation or punctuation.
    """

    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",  # Use latest stable alias
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0, candidate_count=1, max_output_tokens=10
                ),
            )
            prediction = (response.text or "").strip().lower()

            for cat in VALID_CATEGORIES:
                if cat in prediction:
                    return cat
            return "neutral"

        except Exception as e:  # pylint: disable=broad-exception-caught
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (2**attempt)
                    time.sleep(sleep_time)
                    continue

            print(f"API Error (Attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"FAILED sample: {text[:50]}...")
                return "api_error"
            time.sleep(1)

    return "hallucination_error"


def main():
    """Main function to run the Gemini baseline evaluation."""
    print("=" * 80)
    print("SentinelAI Gemini Flash Baseline Evaluation")
    print("=" * 80)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    # Initialise Client
    client = genai.Client(api_key=api_key)

    # Paths
    dataset_path = get_dataset_path("sentinelai_dataset_v0.2.json")
    output_dir = config.EVAL_DIR
    output_dir.mkdir(exist_ok=True)

    # Load raw data (Exact same logic as baseline_keyword.py for 1:1 alignment)
    print(f"Loading test dataset from {dataset_path.name}...")

    with open(dataset_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    v01_path = get_dataset_path("sentinelai_dataset_v0.1.json")
    with open(v01_path, "r", encoding="utf-8") as f:
        data_v01 = json.load(f)

    # Reproduce the exact mixed dataset used in training/eval
    torch.manual_seed(config.SEED)
    v02_indices = torch.randperm(len(full_data))[:2000].tolist()
    mixed_data = data_v01.copy()
    mixed_data.extend([full_data[i] for i in v02_indices])

    # Reproduce the shuffle and split
    torch.manual_seed(config.DATASET_SEED)
    indices = torch.randperm(len(mixed_data)).tolist()
    shuffled_data = [mixed_data[i] for i in indices]

    # Take the last 10% (Test set)
    test_start = int(len(shuffled_data) * 0.9)
    test_data = shuffled_data[test_start:]

    print(f"Processing {len(test_data)} test samples with Gemini 2.5 Flash Lite...")

    y_pred = []
    y_true = []

    # Reverse map for printing
    inv_category_map = {v: k for k, v in CATEGORY_MAP.items()}

    # Progress bar for API calls
    failures = 0
    for item in tqdm(test_data, desc="Classifying"):
        message = item["message"]
        if "timestamp" in item and item["timestamp"]:
            message = f"[{item['timestamp']}] {message}"

        true_label_str = item["category"]
        true_label = CATEGORY_MAP[true_label_str]

        # Call Gemini
        pred_label_str = classify_message_with_gemini(client, message)

        # Map string back to index
        if pred_label_str in CATEGORY_MAP:
            pred_label = CATEGORY_MAP[pred_label_str]
        else:
            failures += 1
            # Log specific failure type
            if pred_label_str == "api_error":
                print("Sample failed due to API Error.")
            elif pred_label_str == "hallucination_error":
                print("Sample failed due to hallucination/unrecognised output.")

            pred_label = (
                0  # Default to neutral for metrics calculation, but tracked in failures
            )

        y_true.append(true_label)
        y_pred.append(pred_label)

        # Small sleep just to be polite, though Flash is fast
        time.sleep(0.05)

    print(f"\nTotal Failures (API/Hallucination): {failures}/{len(test_data)}")
    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(
        y_true,
        y_pred,
        target_names=[inv_category_map[i] for i in range(7)],
        output_dict=True,
        zero_division=0,
    )

    # Calculate macro/weighted averages manually
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(7)), zero_division=0
    )

    macro_avg = {
        "precision": float(np.mean(precision)),
        "recall": float(np.mean(recall)),
        "f1_score": float(np.mean(f1)),
    }

    print("\n" + "=" * 80)
    print("GEMINI FLASH BASELINE RESULTS")
    print("=" * 80)
    print(f"Overall Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_avg['f1_score']:.4f}\n")

    per_class_results = {}
    for i in range(7):
        cat = inv_category_map[i]
        metrics = cast(Dict[str, Any], report)[cat]
        per_class_results[cat] = {
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "f1_score": float(metrics["f1-score"]),
            "support": int(metrics["support"]),
        }

    # Save results
    results = {
        "category_classification": {
            "accuracy": float(accuracy),
            "macro_avg": macro_avg,
            "per_class": per_class_results,
            "confusion_matrix": cm.tolist(),
        },
        "model_info": {
            "name": "gemini-flash-lite-latest",
            "samples": len(test_data),
            "failures": failures,
        },
    }

    output_path = output_dir / "baseline_gemini_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
