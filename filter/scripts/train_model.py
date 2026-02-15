"""
Training Script for Dual-Head BERT Classifier

Trains the BERT model with LoRA fine-tuning on the mental health dataset.
Logs training metrics to JSON for experiment tracking.
"""

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict

import torch
import torch.nn as nn
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
from peft import LoraConfig, get_peft_model, TaskType

sys.path.append(str(Path(__file__).parent.parent))

from models.dual_head_classifier import DualHeadBERTClassifier
from services.dataset_loader import load_dataset

# Hyperparameters
CONFIG = {
    "model_name": "bert-base-uncased",
    "num_category_classes": 7,
    "num_severity_classes": 4,
    "batch_size": 16,
    "learning_rate": 3e-4,
    "num_epochs": 3,
    "max_length": 128,
    "lora_r": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.1,
    "seed": 42
}


def train_epoch(
    model: nn.Module,
    loader,
    optimizer,
    scheduler,
    device: torch.device,
    category_criterion: nn.Module,
    severity_criterion: nn.Module
) -> float:
    """
    Train model for one epoch.
    
    Args:
        model: The model to train
        loader: DataLoader for training data
        optimizer: Optimizer
        scheduler: Learning rate scheduler
        device: Device to train on
        category_criterion: Loss function for category classification
        severity_criterion: Loss function for severity classification
    
    Returns:
        Average loss for the epoch
    """
    model.train()
    total_loss = 0

    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        category_labels = batch["category_label"].to(device)
        severity_labels = batch["severity_label"].to(device)

        optimizer.zero_grad()

        category_logits, severity_logits = model(input_ids, attention_mask)

        loss_category = category_criterion(category_logits, category_labels)
        loss_severity = severity_criterion(severity_logits, severity_labels)
        loss = loss_category + loss_severity

        loss.backward()
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()

    return total_loss / len(loader)


def evaluate(
    model: nn.Module,
    loader,
    device: torch.device,
    category_criterion: nn.Module,
    severity_criterion: nn.Module
) -> Dict[str, float]:
    """
    Evaluate model on validation/test set.
    
    Args:
        model: The model to evaluate
        loader: DataLoader for evaluation data
        device: Device to evaluate on
        category_criterion: Loss function for category classification
        severity_criterion: Loss function for severity classification
    
    Returns:
        Dictionary with loss and accuracy metrics
    """
    model.eval()
    total_loss = 0
    correct_category = 0
    correct_severity = 0
    total = 0

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            category_labels = batch["category_label"].to(device)
            severity_labels = batch["severity_label"].to(device)

            category_logits, severity_logits = model(input_ids, attention_mask)

            loss_category = category_criterion(category_logits, category_labels)
            loss_severity = severity_criterion(severity_logits, severity_labels)
            loss = loss_category + loss_severity

            total_loss += loss.item()

            # Calculate accuracy
            _, category_preds = torch.max(category_logits, 1)
            _, severity_preds = torch.max(severity_logits, 1)

            correct_category += (category_preds == category_labels).sum().item()
            correct_severity += (severity_preds == severity_labels).sum().item()
            total += category_labels.size(0)

    return {
        "loss": total_loss / len(loader),
        "category_accuracy": correct_category / total,
        "severity_accuracy": correct_severity / total
    }


def main():
    """Main training function."""
    print("=" * 80)
    print("SentinelAI BERT Filter Training")
    print("=" * 80)

    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Load dataset
    print("\nLoading dataset...")
    dataset_path = Path(__file__).parent.parent.parent / "datasets" / "sentinelai_dataset_v0.2.json"
    train_loader, val_loader, test_loader, tokenizer = load_dataset(
        str(dataset_path),
        model_name=CONFIG["model_name"],
        max_length=CONFIG["max_length"],
        seed=CONFIG["seed"]
    )

    # Initialize model
    print("\nInitializing model...")
    model = DualHeadBERTClassifier(
        model_name=CONFIG["model_name"],
        num_category_classes=CONFIG["num_category_classes"],
        num_severity_classes=CONFIG["num_severity_classes"]
    )

    # Apply LoRA to BERT backbone
    lora_config = LoraConfig(
        r=CONFIG["lora_r"],
        lora_alpha=CONFIG["lora_alpha"],
        target_modules=["query", "value"],
        lora_dropout=CONFIG["lora_dropout"],
        bias="none",
        task_type=TaskType.FEATURE_EXTRACTION
    )
    model.bert = get_peft_model(model.bert, lora_config)
    model.to(device)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Trainable parameters: {trainable_params:,} / {total_params:,} ({100 * trainable_params / total_params:.2f}%)")  # pylint: disable=line-too-long

    # Setup optimizer and scheduler
    optimizer = AdamW(model.parameters(), lr=CONFIG["learning_rate"])
    total_steps = len(train_loader) * CONFIG["num_epochs"]
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=0,
        num_training_steps=total_steps
    )

    # Loss functions
    category_criterion = nn.CrossEntropyLoss()
    severity_criterion = nn.CrossEntropyLoss()

    # Training loop
    print("\n" + "=" * 80)
    print("Starting training...")
    print("=" * 80)

    training_log = {
        "experiment_id": f"bert_dual_head_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "config": CONFIG,
        "device": str(device),
        "epochs": []
    }

    for epoch in range(CONFIG["num_epochs"]):
        print(f"\nEpoch {epoch + 1}/{CONFIG['num_epochs']}")
        print("-" * 80)

        train_loss = train_epoch(
            model, train_loader, optimizer, scheduler, device,
            category_criterion, severity_criterion
        )

        val_metrics = evaluate(
            model, val_loader, device,
            category_criterion, severity_criterion
        )

        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_metrics['loss']:.4f}")
        print(f"Val Category Acc: {val_metrics['category_accuracy']:.4f}")
        print(f"Val Severity Acc: {val_metrics['severity_accuracy']:.4f}")

        training_log["epochs"].append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "val_category_acc": val_metrics["category_accuracy"],
            "val_severity_acc": val_metrics["severity_accuracy"]
        })

    # Final test evaluation
    print("\n" + "=" * 80)
    print("Final Test Evaluation")
    print("=" * 80)

    test_metrics = evaluate(
        model, test_loader, device,
        category_criterion, severity_criterion
    )

    print(f"Test Loss: {test_metrics['loss']:.4f}")
    print(f"Test Category Acc: {test_metrics['category_accuracy']:.4f}")
    print(f"Test Severity Acc: {test_metrics['severity_accuracy']:.4f}")

    training_log["final_test_metrics"] = test_metrics

    # Save model
    model_dir = Path(__file__).parent.parent / "models"
    model_dir.mkdir(exist_ok=True)

    # Save LoRA adapters
    lora_path = model_dir / "lora_adapters"
    model.bert.save_pretrained(str(lora_path))
    print(f"\nLoRA adapters saved to: {lora_path}")

    # Save full model state
    model_path = model_dir / "dual_head_classifier.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": CONFIG,
        "category_classes": CONFIG["num_category_classes"],
        "severity_classes": CONFIG["num_severity_classes"]
    }, str(model_path))
    print(f"Model checkpoint saved to: {model_path}")

    # Save training log
    log_path = model_dir / "training_log.json"
    with open(log_path, 'w') as f:
        json.dump(training_log, f, indent=2)
    print(f"Training log saved to: {log_path}")

    print("\n" + "=" * 80)
    print("Training complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
