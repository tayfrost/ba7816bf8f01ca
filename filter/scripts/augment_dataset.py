"""
Dataset Augmentation Script

Uses nlpaug to paraphrase messages and increase lexical diversity (TTR).
Generates 2 paraphrased versions per original message while preserving labels.
"""

# pylint: disable=line-too-long
# pylint: disable=wrong-import-position

import json
import random
import sys
from pathlib import Path
from typing import Dict, List

import nlpaug.augmenter.word as naw
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import get_dataset_path

# Configuration
CONFIG = {
    "input_path": get_dataset_path("sentinelai_dataset_v0.1.json"),
    "output_path": config.DATASETS_DIR / "sentinelai_dataset_v0.2_augmented.json",
    "paraphrases_per_message": 2,
    "seed": config.SEED,
}


def load_dataset(path: str) -> List[Dict]:
    """Load dataset from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_augmenters():
    """
    Create nlpaug augmenters for paraphrasing.

    Uses contextual word embeddings for synonym replacement.
    """
    # Synonym augmenter using contextual embeddings
    aug_substitute = naw.ContextualWordEmbsAug(
        model_path=config.MODEL_NAME, action="substitute", aug_p=0.3
    )

    return aug_substitute


def augment_message(message: str, augmenter, num_paraphrases: int = 2) -> List[str]:
    """
    Generate paraphrased versions of a message.

    Args:
        message: Original message text
        augmenter: nlpaug augmenter instance
        num_paraphrases: Number of paraphrases to generate

    Returns:
        List of paraphrased messages
    """
    paraphrases = []

    # Generate multiple paraphrases
    for _ in range(num_paraphrases):
        try:
            augmented = augmenter.augment(message)
            if isinstance(augmented, list):
                augmented = augmented[0]
            paraphrases.append(augmented)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Warning: Augmentation failed for '{message[:50]}...': {e}")
            paraphrases.append(message)

    return paraphrases


def augment_dataset(
    data: List[Dict], augmenter, paraphrases_per_message: int
) -> List[Dict]:
    """
    Augment entire dataset with paraphrased messages.

    Args:
        data: Original dataset
        augmenter: nlpaug augmenter instance
        paraphrases_per_message: Number of paraphrases per message

    Returns:
        Augmented dataset with original + paraphrased messages
    """
    augmented_data = []

    # Keep all original messages
    augmented_data.extend(data)

    print(
        f"Augmenting {len(data)} messages with {paraphrases_per_message} paraphrases each..."
    )

    # Generate paraphrases
    for item in tqdm(data, desc="Generating paraphrases"):
        message = item["message"]
        paraphrases = augment_message(message, augmenter, paraphrases_per_message)

        for i, paraphrased_message in enumerate(paraphrases):
            # Create new item with paraphrased message but same labels
            augmented_item = item.copy()
            augmented_item["id"] = f"{item['id']}_aug{i + 1}"
            augmented_item["message"] = paraphrased_message
            augmented_data.append(augmented_item)

    return augmented_data


def calculate_ttr_quick(messages: List[str]) -> float:
    """Quick TTR calculation for validation."""
    all_tokens = []
    for msg in messages:
        tokens = msg.lower().split()
        all_tokens.extend(tokens)

    if len(all_tokens) == 0:
        return 0.0

    return len(set(all_tokens)) / len(all_tokens)


def main():
    """Main augmentation pipeline."""
    print("=" * 80)
    print("DATASET AUGMENTATION - Improving Lexical Diversity")
    print("=" * 80)

    # Set random seed
    random.seed(CONFIG["seed"])

    # Load original dataset
    dataset_path = CONFIG["input_path"]
    print(f"\nLoading dataset from: {dataset_path}")
    data = load_dataset(str(dataset_path))
    print(f"Original dataset: {len(data)} examples")

    # Calculate original TTR
    original_messages = [item["message"] for item in data]
    original_ttr = calculate_ttr_quick(original_messages)
    print(f"Original TTR: {original_ttr:.4f}")

    # Create augmenter
    print("\nInitializing nlpaug augmenter...")
    augmenter = create_augmenters()

    # Augment dataset
    augmented_data = augment_dataset(data, augmenter, CONFIG["paraphrases_per_message"])
    print(f"\nAugmented dataset: {len(augmented_data)} examples")
    print(f"Increase: {len(augmented_data) - len(data)} new examples")

    # Calculate new TTR
    augmented_messages = [item["message"] for item in augmented_data]
    augmented_ttr = calculate_ttr_quick(augmented_messages)
    print(f"\nAugmented TTR: {augmented_ttr:.4f}")
    print(
        f"TTR improvement: {augmented_ttr - original_ttr:.4f} ({(augmented_ttr / original_ttr - 1) * 100:.1f}% increase)"
    )

    # Save augmented dataset
    output_path = CONFIG["output_path"]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(augmented_data, f, indent=2)

    print(f"\n✓ Augmented dataset saved to: {output_path}")

    # Summary
    print("\n" + "=" * 80)
    print("AUGMENTATION COMPLETE")
    print("=" * 80)
    print(f"Original:  {len(data):5d} examples | TTR: {original_ttr:.4f}")
    print(f"Augmented: {len(augmented_data):5d} examples | TTR: {augmented_ttr:.4f}")
    print(
        f"\n{'✅ TTR > threshold' if augmented_ttr > 0.3 else '⚠️  TTR still below threshold'}"
    )
    print("\n🎯 Next: Re-run EDA notebook on v0.2_augmented.json to verify quality")


if __name__ == "__main__":
    main()
