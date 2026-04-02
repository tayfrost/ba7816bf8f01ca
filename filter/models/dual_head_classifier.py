"""
Dual-Head BERT Classifier for Mental Health Risk Detection

This module implements a BERT-based classifier with two classification heads:
1. Category classification (7 classes: neutral, humor_sarcasm, stress, burnout,
   depression, harassment, suicidal_ideation)
2. Severity classification (4 stages: none, early, middle, late)

The model uses LoRA (Low-Rank Adaptation) for efficient fine-tuning of the BERT backbone.
"""

# pylint: disable=wrong-import-position

import sys
from pathlib import Path
from typing import Tuple

import torch
from torch import nn
from transformers import AutoModel

# Add parent directory to path to allow importing config
sys.path.append(str(Path(__file__).parent.parent))

import config


class DualHeadBERTClassifier(nn.Module):
    """
    BERT-based classifier with dual classification heads for category and severity.

    Architecture:
    - BERT backbone (from config.MODEL_NAME)
    - Two independent linear classification heads
    - Uses [CLS] token representation for classification

    Args:
        model_name (str): Pretrained BERT model name
        num_category_classes (int): Number of category classes
        num_severity_classes (int): Number of severity stages
    """

    def __init__(
        self,
        model_name: str = config.MODEL_NAME,
        num_category_classes: int = config.NUM_CATEGORY_CLASSES,
        num_severity_classes: int = config.NUM_SEVERITY_CLASSES,
    ):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size

        # Category classification head
        self.category_classifier = nn.Linear(hidden_size, num_category_classes)

        # Severity classification head
        self.severity_classifier = nn.Linear(hidden_size, num_severity_classes)

        self.num_category_classes = num_category_classes
        self.num_severity_classes = num_severity_classes

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the model.

        Args:
            input_ids (torch.Tensor): Input token IDs [batch_size, seq_len]
            attention_mask (torch.Tensor): Attention mask [batch_size, seq_len]

        Returns:
            Tuple[torch.Tensor, torch.Tensor]:
                - category_logits: [batch_size, num_category_classes]
                - severity_logits: [batch_size, num_severity_classes]
        """
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.last_hidden_state[:, 0, :]  # [CLS] token

        category_logits = self.category_classifier(pooled_output)
        severity_logits = self.severity_classifier(pooled_output)

        return category_logits, severity_logits
