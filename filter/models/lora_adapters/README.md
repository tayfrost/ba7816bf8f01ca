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

- **GPU:** NVIDIA GeForce GTX 1080 (8GB VRAM)
- **Training Time:** ~3 minutes (1 min/epoch)
- **Training Regime:** fp32

## Results

### Test Set Performance

| Metric | Score |
| :----- | :---- |
| **Category Accuracy** | 76.29% |
| **Severity Accuracy** | 78.29% |
| **Test Loss** | 1.1840 |

**Performance Context:**

- Category: 5.3x better than random (7-class baseline: 14.3%)
- Severity: 3.1x better than random (4-class baseline: 25%)
- Low/no overfitting: Test accuracy matches validation accuracy

## Usage

### Loading the Model

```python
from pathlib import Path
import torch
from peft import PeftModel
from transformers import AutoModel, AutoTokenizer

# Import custom dual-head classifier
from models.dual_head_classifier import DualHeadBERTClassifier

# Initialise model
model = DualHeadBERTClassifier(
    model_name="bert-base-uncased",
    num_category_classes=7,
    num_severity_classes=4
)

# Load LoRA adapters
adapter_path = "filter/models/lora_adapters"
model.bert = PeftModel.from_pretrained(model.bert, adapter_path)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Inference
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

message = "I'm completely overwhelmed with work and can't sleep anymore"
inputs = tokenizer(
    message,
    padding="max_length",
    truncation=True,
    max_length=128,
    return_tensors="pt"
).to(device)

with torch.no_grad():
    category_logits, severity_logits = model(
        inputs["input_ids"],
        inputs["attention_mask"]
    )
    
    category_pred = torch.argmax(category_logits, dim=1).item()
    severity_pred = torch.argmax(severity_logits, dim=1).item()

# Category mapping: 0=neutral, 1=humor_sarcasm, 2=stress, 3=burnout, 
#                   4=depression, 5=harassment, 6=suicidal_ideation
# Severity mapping: 0=none, 1=early, 2=middle, 3=late
```

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

Full implementation: [SentinelAI Repository](https://github.kcl.ac.uk/k24000626/SentinelAI)

Branch: `feature/filter`

### Framework versions

- PEFT 0.18.1
