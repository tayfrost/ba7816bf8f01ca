"""
Dataset Loader for SentinelAI Mental Health Dataset

Loads and preprocesses the synthetic mental health dataset for BERT training.
Handles tokenization, label encoding, and PyTorch dataset creation.
"""

from typing import Dict, List, Tuple
import json
from pathlib import Path

from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer

import torch


# Category to index mapping
CATEGORY_MAP = {
    "neutral": 0,
    "humor_sarcasm": 1,
    "stress": 2,
    "burnout": 3,
    "depression": 4,
    "harassment": 5,
    "suicidal_ideation": 6
}

# Severity stage to index mapping
SEVERITY_MAP = {
    "none": 0,
    "early": 1,
    "middle": 2,
    "late": 3
}

# Risk categories (for binary routing logic)
RISK_CATEGORIES = {"stress", "burnout", "depression", "harassment", "suicidal_ideation"}


class MentalHealthDataset(Dataset):
    """
    PyTorch Dataset for mental health risk detection.
    
    Args:
        data (List[Dict]): List of dataset examples
        tokenizer: HuggingFace tokenizer
        max_length (int): Maximum sequence length for tokenization
    """

    def __init__(self, data: List[Dict], tokenizer, max_length: int = 128):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = self.data[idx]

        # Tokenize message
        encoding = self.tokenizer(
            item["message"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        # Convert labels to indices
        category_label = CATEGORY_MAP[item["category"]]
        severity_label = SEVERITY_MAP[item["stage"]]

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "category_label": torch.tensor(category_label, dtype=torch.long),
            "severity_label": torch.tensor(severity_label, dtype=torch.long),
            "is_risk": torch.tensor(item["is_risk"], dtype=torch.long)
        }


def load_dataset(
    dataset_path: str,
    model_name: str = "bert-base-uncased",
    train_split: float = 0.8,
    val_split: float = 0.1,
    max_length: int = 128,
    seed: int = 42,
    mix_datasets: bool = True
) -> Tuple[DataLoader, DataLoader, DataLoader, AutoTokenizer]:
    """
    Load and split the mental health dataset.
    
    Args:
        dataset_path (str): Path to dataset JSON file (v0.1 or v0.2)
        model_name (str): Pretrained model name for tokenizer
        train_split (float): Training set proportion
        val_split (float): Validation set proportion
        max_length (int): Maximum sequence length
        seed (int): Random seed for reproducibility
        mix_datasets (bool): If True, mix v0.1 (5k) + v0.2 (2k random) = 7k total
    
    Returns:
        Tuple of (train_loader, val_loader, test_loader, tokenizer)
    """
    # Load dataset(s)
    if mix_datasets:
        # Mix v0.1 (all 5k) + v0.2 (random 2k) for balanced quality + diversity
        dataset_dir = Path(dataset_path).parent
        v01_path = dataset_dir / "sentinelai_dataset_v0.1.json"
        v02_path = dataset_dir / "sentinelai_dataset_v0.2.json"

        with open(v01_path, 'r') as f:
            data_v01 = json.load(f)

        with open(v02_path, 'r') as f:
            data_v02 = json.load(f)

        # Keep all v0.1 (natural phrasing)
        data = data_v01.copy()

        # Add 2000 random samples from v0.2 (diversity boost)
        torch.manual_seed(seed)
        v02_indices = torch.randperm(len(data_v02))[:2000].tolist()
        data.extend([data_v02[i] for i in v02_indices])

        print(f"Mixed dataset: {len(data_v01)} v0.1 + {len(v02_indices)} v0.2 = {len(data)} total")
    else:
        with open(dataset_path, 'r') as f:
            data = json.load(f)
        print(f"Loaded dataset: {len(data)} examples from {Path(dataset_path).name}")

    # Shuffle data
    torch.manual_seed(seed)
    indices = torch.randperm(len(data)).tolist()
    data = [data[i] for i in indices]

    # Split data
    n = len(data)
    train_end = int(n * train_split)
    val_end = train_end + int(n * val_split)

    train_data = data[:train_end]
    val_data = data[train_end:val_end]
    test_data = data[val_end:]

    # Initialize tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Create datasets
    train_dataset = MentalHealthDataset(train_data, tokenizer, max_length)
    val_dataset = MentalHealthDataset(val_data, tokenizer, max_length)
    test_dataset = MentalHealthDataset(test_data, tokenizer, max_length)

    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    print(f"Dataset loaded: {len(train_data)} train, {len(val_data)} val, {len(test_data)} test")

    return train_loader, val_loader, test_loader, tokenizer


def get_class_distribution(dataset_path: str) -> Dict[str, int]:
    """
    Get class distribution for the dataset.
    
    Args:
        dataset_path (str): Path to dataset JSON file
    
    Returns:
        Dict with category and severity distributions
    """
    with open(dataset_path, 'r') as f:
        data = json.load(f)

    category_dist = {}
    severity_dist = {}
    risk_dist = {"risk": 0, "no_risk": 0}

    for item in data:
        category = item["category"]
        severity = item["stage"]
        is_risk = item["is_risk"]

        category_dist[category] = category_dist.get(category, 0) + 1
        severity_dist[severity] = severity_dist.get(severity, 0) + 1
        risk_dist["risk" if is_risk else "no_risk"] += 1

    return {
        "categories": category_dist,
        "severity": severity_dist,
        "risk": risk_dist,
        "total": len(data)
    }
