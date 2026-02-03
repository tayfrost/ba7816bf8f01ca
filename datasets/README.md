# SentinelAI HR Risk Dataset v2.0

## Overview
Synthetic workplace mental health dataset for training early-warning detection systems.
Clinically grounded, with timestamp data for temporal analysis.

## Key Stats
| Metric | Value |
|--------|-------|
| Total examples | 1,005 |
| Risk messages | 610 (61%) |
| Neutral / True negatives | 395 (39%) |
| Late-night messages (00:00-05:00) | 173 |

## Categories

| Category | Count | Clinical Basis |
|----------|-------|----------------|
| `neutral` | 210 | Normal workplace communication |
| `humor_sarcasm` | 185 | Dark humor distinguishable from real distress |
| `stress` | 139 | Acute/chronic stress response, physiological markers |
| `depression` | 127 | DSM-5 Major Depressive Disorder criteria |
| `burnout` | 124 | Maslach Burnout Inventory (MBI) |
| `harassment` | 119 | UK Equality Act 2010, workplace bullying literature |
| `suicidal_ideation` | 101 | Clinical suicide risk assessment frameworks |

## Severity Stages
- **early**: Subtle signs, easily dismissed → `monitor`
- **middle**: Clear symptoms, functional impact → `hr_review`
- **late**: Crisis level → `urgent_hr_intervention` or `immediate_crisis_intervention`

## Columns

| Column | Description |
|--------|-------------|
| `id` | Unique identifier |
| `timestamp` | YYYY-MM-DD HH:MM (simulated, realistic distribution) |
| `message` | Simulated workplace message |
| `category` | Risk category |
| `stage` | early / middle / late / none |
| `severity_score` | 0-10 scale |
| `is_risk` | Binary (1=risk, 0=neutral/humor) |
| `recommended_action` | Suggested response (kept for reference, not primary) |
| `context` | slack / email |
| `clinical_basis` | Clinical/theoretical grounding |

## Timestamp Logic
- **Normal messages**: Working hours (8am-6pm)
- **Early stage**: Slight extension into evenings
- **Middle stage**: Evening hours, some late night
- **Late stage / Crisis**: Significant late-night representation (00:00-05:00)
- **Suicidal ideation (late)**: Heavy late-night weighting

This enables temporal analysis: same message at 10am vs 3am carries different weight.

## humor_sarcasm Category
Critical for reducing false positives. Examples include:
- "This deadline is killing me lol" → humor
- "My code has imposter syndrome" → humor
- Explicit markers: "kidding", "joking", meme formats

The model must distinguish workplace dark humor from genuine distress signals.

## Usage Notes
1. UK English workplace context (Slack/email style)
2. Timestamps enable time-of-day feature engineering
3. `recommended_action` kept but not primary focus
4. `humor_sarcasm` is crucial for false-positive reduction

## Ethical Positioning
- Synthetic data only - no real PII
- Support-focused, not punitive
- Human-in-the-loop required for all alerts

## Version History
- v1.0: Initial release (400 examples)
- v2.0: Added timestamps, humor_sarcasm category, expanded to 1,005 examples
