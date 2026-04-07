"""
Training Script for Dual-Head BERT Classifier

Trains the BERT model with LoRA fine-tuning on the mental health dataset.
Logs training metrics to JSON for experiment tracking.
"""

# pylint: disable=wrong-import-position

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import torch
import torch.nn as nn
from peft import get_peft_model
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup

import wandb

try:
    import peft.tuners.tuners_utils
    peft.tuners.tuners_utils._torch_supports_distributed = False
except ImportError:
    pass

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import config
from services.dataset_loader import load_dataset, get_dataset_path
from services.model_factory import create_raw_model, get_lora_config


def train_epoch(
    model: nn.Module,
    loader,
    optimizer,
    scheduler,
    device: torch.device,
    category_criterion: nn.Module,
    severity_criterion: nn.Module,
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
    severity_criterion: nn.Module,
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
        "severity_accuracy": correct_severity / total,
    }


def main() -> None:
    """Main training function."""
    print("=" * 80)
    print("SentinelAI BERT Filter Training")
    print("=" * 80)

    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Load dataset
    print("\nLoading dataset...")
    dataset_path = get_dataset_path("sentinelai_dataset_v0.2.json")
    train_loader, val_loader, test_loader, _ = load_dataset(
        str(dataset_path),
        model_name=config.MODEL_NAME,
        max_length=config.MAX_LENGTH,
        seed=config.SEED,
    )

    # Initialise model
    print("\nInitialising model...")
    model = create_raw_model()

    # Apply LoRA to BERT backbone
    lora_config = get_lora_config()
    model.bert = get_peft_model(model.bert, lora_config)
    model.to(device)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(
        "Trainable parameters: "
        f"{trainable_params:,} / {total_params:,} "
        f"({100 * trainable_params / total_params:.2f}%)",
    )

    # Setup optimiser and scheduler
    optimizer = AdamW(model.parameters(), lr=config.LEARNING_RATE)
    total_steps = len(train_loader) * config.NUM_EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=0, num_training_steps=total_steps
    )

    # Loss functions
    category_criterion = nn.CrossEntropyLoss()
    severity_criterion = nn.CrossEntropyLoss()

    training_log = {
        "experiment_id": f"bert_dual_head_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "config": {
            "model_name": config.MODEL_NAME,
            "num_category_classes": config.NUM_CATEGORY_CLASSES,
            "num_severity_classes": config.NUM_SEVERITY_CLASSES,
            "batch_size": config.BATCH_SIZE,
            "learning_rate": config.LEARNING_RATE,
            "num_epochs": config.NUM_EPOCHS,
            "max_length": config.MAX_LENGTH,
            "lora_r": config.LORA_R,
            "lora_alpha": config.LORA_ALPHA,
            "lora_dropout": config.LORA_DROPOUT,
            "seed": config.SEED,
        },
        "device": str(device),
        "epochs": [],
    }

    # Initialise WandB
    if config.USE_WANDB:
        wandb.init(
            project=config.WANDB_PROJECT,
            name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config=training_log["config"],
        )

    # Training loop
    print("\n" + "=" * 80)
    print("Starting training...")
    print("=" * 80)

    for epoch in range(config.NUM_EPOCHS):
        print(f"\nEpoch {epoch + 1}/{config.NUM_EPOCHS}")
        print("-" * 80)

        train_loss = train_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            device,
            category_criterion,
            severity_criterion,
        )

        val_metrics = evaluate(
            model, val_loader, device, category_criterion, severity_criterion
        )

        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_metrics['loss']:.4f}")
        print(f"Val Category Acc: {val_metrics['category_accuracy']:.4f}")
        print(f"Val Severity Acc: {val_metrics['severity_accuracy']:.4f}")

        # Log to WandB
        if config.USE_WANDB:
            wandb.log(
                {
                    "epoch": epoch + 1,
                    "train_loss": train_loss,
                    "val_loss": val_metrics["loss"],
                    "val_category_accuracy": val_metrics["category_accuracy"],
                    "val_severity_accuracy": val_metrics["severity_accuracy"],
                }
            )

        training_log["epochs"].append(
            {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "val_loss": val_metrics["loss"],
                "val_category_acc": val_metrics["category_accuracy"],
                "val_severity_acc": val_metrics["severity_accuracy"],
            }
        )

    # Final test evaluation
    print("\n" + "=" * 80)
    print("Final Test Evaluation")
    print("=" * 80)

    test_metrics = evaluate(
        model, test_loader, device, category_criterion, severity_criterion
    )

    print(f"Test Loss: {test_metrics['loss']:.4f}")
    print(f"Test Category Acc: {test_metrics['category_accuracy']:.4f}")
    print(f"Test Severity Acc: {test_metrics['severity_accuracy']:.4f}")

    if config.USE_WANDB:
        wandb.log(
            {
                "test_loss": test_metrics["loss"],
                "test_category_accuracy": test_metrics["category_accuracy"],
                "test_severity_accuracy": test_metrics["severity_accuracy"],
            }
        )
        wandb.finish()

    training_log["final_test_metrics"] = test_metrics

    # Save model
    model_dir = config.MODELS_DIR
    model_dir.mkdir(exist_ok=True)

    # Save LoRA adapters
    lora_path = model_dir / config.ADAPTERS_DIRNAME
    model.bert.save_pretrained(str(lora_path))
    print(f"\nLoRA adapters saved to: {lora_path}")

    # Save full model state
    model_path = model_dir / config.CHECKPOINT_FILENAME
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": training_log["config"],
            "category_classes": config.NUM_CATEGORY_CLASSES,
            "severity_classes": config.NUM_SEVERITY_CLASSES,
        },
        str(model_path),
    )
    print(f"Model checkpoint saved to: {model_path}")

    # Save training log
    log_dir = config.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "training_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(training_log, f, indent=2)
    print(f"Training log saved to: {log_path}")

    print("\n" + "=" * 80)
    print("Training complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
