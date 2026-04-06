"""Topic keyword matching and concern detection."""

import re

TOPIC_KEYWORDS = {
    "workplace_stress": [
        "stress", "stressed", "stressing", "pressure", "overwhelmed", "overwhelming", "workload",
        "deadline", "deadlines", "overwork", "overworked", "demanding", "hectic", "stressful", "under pressure",
    ],
    "burnout": [
        "burnout", "burned out", "exhausted", "drained", "depleted", "tired of work",
        "no energy", "can't cope", "running on empty", "worn out", "cynical about work",
    ],
    "anxiety": [
        "anxious", "anxiety", "nervous", "worried", "worry", "worries", "worrying",
        "panic", "panicking", "fear", "uneasy", "restless", "dread", "on edge", "apprehensive",
    ],
    "depression": [
        "depressed", "depressing", "depression", "sad", "sadness", "hopeless", "empty",
        "no motivation", "worthless", "down", "unmotivated", "failure", "lost interest",
    ],
    "anger_management": [
        "angry", "anger", "furious", "irritated", "irritable", "frustrated", "frustrating",
        "rage", "raging", "annoyed", "hostile", "mad", "snapping", "lose my temper", "resentful",
    ],
    "sleep_issues": [
        "sleep", "insomnia", "can't sleep", "tired", "fatigue", "restless nights",
        "wake up", "shift work", "exhaustion", "not sleeping",
    ],
    "work_life_balance": [
        "balance", "overwork", "boundaries", "personal time", "family time",
        "always working", "never off", "weekends", "after hours", "disconnect",
    ],
    "social_isolation": [
        "lonely", "alone", "isolated", "disconnected", "no friends",
        "remote work lonely", "detached", "nobody to talk to", "left out",
    ],
    "emotional_regulation": [
        "emotions", "emotional", "can't control", "mood swings", "reactive",
        "outburst", "overwhelmed feelings", "overreact", "impulsive",
    ],
    "resilience": [
        "resilience", "bounce back", "tough time", "setback", "recovery",
        "cope", "adapt", "get through this", "overcome", "persevere",
    ],
    "mindfulness": [
        "mindful", "mindfulness", "present", "meditation", "awareness",
        "focus", "centered", "grounded", "calm", "attention",
    ],
    "cognitive_distortions": [
        "negative thoughts", "overthinking", "catastrophizing", "worst case",
        "ruminating", "rumination", "spiraling", "all or nothing",
    ],
    "interpersonal_conflict": [
        "conflict", "argument", "disagreement", "difficult colleague", "toxic",
        "confrontation", "fight", "dispute", "manager", "difficult conversation",
    ],
    "self_compassion": [
        "self-criticism", "too hard on myself", "not good enough", "self-blame",
        "beating myself up", "harsh on myself", "self-doubt", "inner critic",
    ],
    "perfectionism": [
        "perfect", "perfectionist", "mistake", "flaw", "impossible standards",
        "never satisfied", "high standards", "fear of failure",
    ],
    "time_poverty": [
        "no time", "busy", "swamped", "schedule", "late", "behind",
        "too much to do", "overwhelmed with tasks", "time management",
    ],
    "workplace_bullying": [
        "bullying", "bullied", "bully", "bullies", "harassment", "harassed", "harassing",
        "intimidation", "intimidated", "threatened", "mobbing", "picked on", "targeted", "abused at work",
    ],
    "digital_interventions": [
        "app", "online program", "digital", "ehealth", "web-based",
        "self-help app", "computerized", "digital therapy",
    ],
    "act_values": [
        "stuck", "rigid", "avoidance", "acceptance", "values",
        "committed action", "defusion", "act therapy", "psychological flexibility",
    ],
    "occupational_health": [
        "disengaged", "meaningless", "bored at work", "no purpose",
        "job crafting", "engagement", "meaningful work", "prevention",
    ],
    "organizational_culture": [
        "management support", "leadership", "culture", "organizational change",
        "team support", "workplace policy", "manager help", "eap", "psychological safety",
    ],
    "physical_activity": [
        "exercise", "workout", "physical activity", "gym", "running",
        "walking", "movement", "sedentary", "fitness", "active",
    ],
    "expressive_writing": [
        "journal", "journaling", "write about feelings", "expressive writing",
        "diary", "reflection", "writing therapy",
    ],
    "biofeedback": [
        "biofeedback", "hrv", "heart rate variability", "resonance breathing",
        "physiological", "wearable", "breathing exercise",
    ],
}

TOPIC_REGEXES = {
    tid: re.compile(r"\b(" + "|".join(map(re.escape, kws)) + r")\b", re.IGNORECASE)
    for tid, kws in TOPIC_KEYWORDS.items()
}


def detect_concerns(text: str) -> list[str]:
    """Return list of topic IDs detected in the text via keyword matching."""
    return [tid for tid, regex in TOPIC_REGEXES.items() if regex.search(text)]
