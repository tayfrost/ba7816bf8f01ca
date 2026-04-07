---
base_model: bert-base-uncased
library_name: peft
tags:
- mental-health
- burnout-detection
- lora
- dual-head-classifier
- workplace-wellbeing
---

# SentinelAI BERT Filter - LoRA Adapters

LoRA fine-tuned BERT model for employee mental health classification in workplace messages. Part of the SentinelAI system for automated burnout detection via Slack message analysis.

## Model Description

- **Base Model:** bert-base-uncased (110M parameters)
- **Fine-tuning Method:** LoRA (Low-Rank Adaptation)
- **Task:** Dual-head classification (category + severity)
- **Trainable Parameters:** 303,371 / 109,785,611 (0.28%)
- **Developed by:** Team Rocket Number One, King's College London
- **License:** MIT (project-specific)

## Architecture

**Dual-Head Classifier:**

- **Category Head:** 7-class classification
  - neutral, humor_sarcasm, stress, burnout, depression, harassment, suicidal_ideation
- **Severity Head:** 4-stage classification
  - none, early, middle, late
- **Binary Routing:** 5 risk categories trigger escalation to LLM agents

## Training Details

### Dataset

- **Total Examples:** 7,000 (mixed dataset for quality + diversity)
  - 5,000 from v0.1 (natural Slack-style phrasing)
  - 2,000 from v0.2 (lexically diverse, synonym-enhanced)
- **Splits:** 80% train (5,600), 10% val (700), 10% test (700)
- **Lexical Diversity:** TTR 0.35 (exceeds 0.3 quality threshold)
- **Clinical Grounding:** Maslach Burnout Inventory (MBI), DSM-5, UK Equality Act 2010

### Hyperparameters

```yaml
LoRA Configuration:
  r: 8
  lora_alpha: 16
  lora_dropout: 0.1
  target_modules: ["query", "value"]
  task_type: FEATURE_EXTRACTION

Training:
  epochs: 3
  batch_size: 16
  learning_rate: 3e-4
  optimizer: AdamW
  scheduler: Linear warmup + decay
  max_sequence_length: 128
  loss_function: CrossEntropyLoss (category + severity summed)
```

### Hardware & Performance

- **GPU 1:** NVIDIA GeForce GTX 1080 (8GB VRAM)
- **GPU 2:** NVIDIA GeForce RTX 3050 Ti Laptop GPU
- **Training Time:** ~3-4 minutes (1 min/epoch)
- **Training Regime:** fp32

## Results

### Test Set Performance

#### Run 1

| Metric | Score |
| :----- | :---- |
| **Category Accuracy** | 76.29% |
| **Severity Accuracy** | 78.29% |
| **Test Loss** | 1.1840 |

#### Run 2 (with ONNX versions inheriting)

| Metric | Score |
| :----- | :---- |
| **Category Accuracy** | 75.14% |
| **Severity Accuracy** | 79.00% |
| **Test Loss** | 1.2204 |

**Performance Context:**

- Category: 5.3x better than random (7-class baseline: 14.3%)
- Severity: 3.1x better than random (4-class baseline: 25%)
- Low/no overfitting: Test accuracy matches validation accuracy

## Usage

### Loading the Model (Production Pattern)

The repository uses a centralised **Model Factory** to handle architecture initialisation and weight loading. It includes **Auto-Download** logic that pulls the latest checkpoint from Hugging Face Hub if it is not found locally.

```python
import torch
from services.model_factory import load_production_model

# Inference
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# This will:

# 1. Initialise DualHeadBERTClassifier
# 2. Apply LoRA adapters
# 3. Check for 'dual_head_classifier.pt' locally
# 4. If missing, download latest from OguzhanKOG/sentinelai-bert-filter
# 5. Load trained weights and return model in eval mode

model = load_production_model(device=device)

# Model is ready for inference
message = "I'm completely overwhelmed with work and can't sleep anymore"
# ... standard tokenization using config.MODEL_NAME ...
```

### Configuration

All parameters (LoRA rank, Alpha, Model Backbone, Paths) are centralised in `filter/config.py`. To change the backbone or parameters across the entire service, update this file only.

## Limitations

- **Synthetic Training Data:** Model trained on generated examples, not real workplace messages
- **English Only:** No multilingual support
- **Context Window:** Limited to 128 tokens (Slack message-sized)
- **Not a Clinical Tool:** Designed for workplace wellbeing monitoring, not medical diagnosis
- **Bias Risk:** May reflect biases in synthetic data generation process

## Intended Use

**Primary Use Case:** Fast, cost-effective gatekeeper filter in SentinelAI architecture. Routes high-risk messages to expensive LLM agents for detailed analysis, while filtering out low-risk neutral messages.

**Architecture Position:**

```text
Slack Message → BERT Filter (this model) → [if risk] → LLM Agent Analysis → HR Alert
```

**Not Intended For:**

- Clinical diagnosis or medical decision-making
- Standalone mental health assessment
- Real-time crisis intervention (human oversight required)
- Legal or disciplinary actions without human review

## Training Logs

Full training metrics available in `training_log.json`:

- Epoch-by-epoch train/val losses
- Category and severity accuracies per epoch
- Final test set evaluation results

## Repository

Full implementation available in the project repository (Private).

Branch: `feature/filter`

### Framework versions

- PEFT 0.18.1
- Torch 2.5.1+cu121
- Transformers 4.46.3
