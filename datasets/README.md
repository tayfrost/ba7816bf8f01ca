Overview
Comprehensive workplace mental health dataset for training AI-based early-warning systems.
Total Examples: 5,000
Version: 3.0
Date: February 2025
Category Distribution
CategoryCount%neutral1,01720.3%humor_sarcasm93418.7%stress67913.6%burnout62812.6%depression61412.3%harassment58811.8%suicidal_ideation54010.8%
Stage Distribution
StageCount%none1,95139.0%early1,05521.1%middle1,04420.9%late95019.0%
Risk Distribution

Risk messages (is_risk=1): 3,049 (61.0%)
Non-risk messages (is_risk=0): 1,951 (39.0%)

Schema
FieldTypeDescriptionidintUnique identifiertimestampstringYYYY-MM-DD HH:MM formatmessagestringWorkplace communication textcategorystringClassification categorystagestringSeverity stage (none/early/middle/late)severity_scoreint0-10 severity ratingis_riskintBinary risk flag (0/1)recommended_actionstringSuggested interventioncontextstringCommunication channel (slack/email)clinical_basisstringClinical framework reference
Categories Explained
neutral
Normal workplace communication with no mental health concerns.
humor_sarcasm
Workplace humor, memes, and sarcastic comments. Includes markers like "lol", "jk", hyperbole, and self-deprecating jokes. Critical for reducing false positives.
stress
Acute and chronic stress responses ranging from mild anxiety to severe panic symptoms.
burnout
Following Maslach Burnout Inventory (MBI) dimensions: emotional exhaustion, depersonalization, reduced personal accomplishment.
depression
Aligned with DSM-5 criteria: anhedonia, sleep disturbance, cognitive symptoms, hopelessness.
harassment
Based on UK Equality Act 2010: microaggressions, hostile environment, discrimination, bullying.
suicidal_ideation
Clinical staging: passive ideation → active ideation without plan → active ideation with plan/intent.
Recommended Actions
ActionDescriptionnoneNo intervention neededmonitorContinue observationhr_reviewFlag for HR reviewurgent_hr_interventionImmediate HR involvementimmediate_crisis_interventionCrisis response required
Clinical Grounding

Burnout: Maslach Burnout Inventory (MBI)
Depression: DSM-5 Major Depressive Episode criteria
Harassment: UK Equality Act 2010
Suicidal Ideation: Clinical risk assessment frameworks

Usage Notes

Dataset includes diverse communication styles: formal, casual, British English, Gen Z slang, emoji-heavy
Timestamp distribution reflects real workplace patterns (late-stage messages weighted toward night hours)
Designed for UK workplace context but applicable internationally
