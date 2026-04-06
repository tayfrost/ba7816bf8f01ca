---
language:
- en
license: mit
task_categories:
- text-classification
tags:
- mental-health
- workplace-wellbeing
- sentinelai
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: sentinelai_dataset_v0.3.csv
- config_name: v0.2
  data_files:
  - split: train
    path: sentinelai_dataset_v0.2.csv
- config_name: v0.1
  data_files:
  - split: train
    path: sentinelai_dataset_v0.1.csv
---

# SentinelAI Datasets

**Hosted Repository:** [huggingface.co/datasets/OguzhanKOG/sentinelai-datasets](https://huggingface.co/datasets/OguzhanKOG/sentinelai-datasets)

Version: 0.3

## Overview

Comprehensive workplace mental health dataset for training AI-based early-warning systems.

- **Total Examples:** 9,000 (2,942 Slack-style, 6,058 Email-style)
- **Version:** 3.0
- **Date:** March 2026

## Category Distribution

| Category | Count | % |
| :--- | :--- | :--- |
| neutral | 1,817 | 20.2% |
| humor_sarcasm | 1,674 | 18.6% |
| stress | 1,229 | 13.7% |
| burnout | 1,123 | 12.5% |
| depression | 1,109 | 12.3% |
| harassment | 1,058 | 11.8% |
| suicidal_ideation | 990 | 11.0% |

## Stage Distribution

| Stage | Count | % |
| :--- | :--- | :--- |
| none | 3,029 | 33.7% |
| early | 2,011 | 22.3% |
| middle | 2,287 | 25.4% |
| late | 1,673 | 18.6% |

## Risk Distribution

- **Risk messages (`is_risk=1`):** 5,971 (66.3%)
- **Non-risk messages (`is_risk=0`):** 3,029 (33.7%)

## Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | int | Unique identifier |
| `timestamp` | string | YYYY-MM-DD HH:MM format |
| `message` | string | Workplace communication text |
| `category` | string | Classification category |
| `stage` | string | Severity stage (none/early/middle/late) |
| `severity_score` | int | 0-10 severity rating |
| `is_risk` | int | Binary risk flag (0/1) |
| `recommended_action` | string | Suggested intervention |
| `context` | string | Communication channel (slack/email) |
| `clinical_basis` | string | Clinical framework reference |

## Categories Explained

### `neutral`

Normal workplace communication with no mental health concerns.

### `humor_sarcasm`

Workplace humor, memes, and sarcastic comments. Includes markers like "lol", "jk", hyperbole, and self-deprecating jokes. Critical for reducing false positives.

### `stress`

Acute and chronic stress responses ranging from mild anxiety to severe panic symptoms.

### `burnout`

Following Maslach Burnout Inventory (MBI) dimensions: emotional exhaustion, depersonalization, reduced personal accomplishment.

### `depression`

Aligned with DSM-5 criteria: anhedonia, sleep disturbance, cognitive symptoms, hopelessness.

### `harassment`

Based on UK Equality Act 2010: microaggressions, hostile environment, discrimination, bullying.

### `suicidal_ideation`

Clinical staging: passive ideation → active ideation without plan → active ideation with plan/intent.

## Recommended Actions

| Action | Description |
| :--- | :--- |
| `none` | No intervention needed |
| `monitor` | Continue observation |
| `hr_review` | Flag for HR review |
| `urgent_hr_intervention` | Immediate HR involvement |
| `immediate_crisis_intervention` | Crisis response required |

## Clinical Grounding

- **Burnout:** Maslach Burnout Inventory (MBI)
- **Depression:** DSM-5 Major Depressive Episode criteria
- **Harassment:** UK Equality Act 2010
- **Suicidal Ideation:** Clinical risk assessment frameworks

## Usage Notes

- Dataset includes diverse communication styles: formal, casual, British English, Gen Z slang, emoji-heavy.
- Timestamp distribution reflects real workplace patterns (late-stage messages weighted toward night hours).
- Designed for UK workplace context but applicable internationally.
