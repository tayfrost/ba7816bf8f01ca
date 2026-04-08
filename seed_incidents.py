#!/usr/bin/env python3
"""
Seed fake incident + score data for a company.

Usage (run from repo root, inside or outside Docker):
    python seed_incidents.py <company_id>

Env vars (override defaults):
    DATABASE_URL   — full postgres DSN
    POSTGRES_PASSWORD  — used to build DSN if DATABASE_URL not set
    POSTGRES_HOST      — default: localhost
    POSTGRES_PORT      — default: 5432
    POSTGRES_DB        — default: sentinelai
    POSTGRES_USER      — default: postgres

What it does:
  - Looks up all active users for the given company
  - For each of the last 7 days, inserts 1 message_incident + 1 incident_scores per user
  - Scores are randomised but plausible (softmax-style, sum ≈ 1)
  - Each user has a random "stress profile" so the graphs look varied
"""

import os
import sys
import uuid
import random
import json
from datetime import datetime, timedelta, timezone

import psycopg

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def build_dsn() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host     = os.environ.get("POSTGRES_HOST", "localhost")
    port     = os.environ.get("POSTGRES_PORT", "5432")
    db       = os.environ.get("POSTGRES_DB", "sentinelai")
    user     = os.environ.get("POSTGRES_USER", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# ---------------------------------------------------------------------------
# Score generation
# ---------------------------------------------------------------------------

CATEGORIES = ["neutral", "humor_sarcasm", "stress", "burnout",
              "depression", "harassment", "suicidal_ideation"]

SEVERITY_LABELS = ["none", "early", "middle", "late"]


def softmax(values: list[float]) -> list[float]:
    import math
    exps = [math.exp(v) for v in values]
    total = sum(exps)
    return [e / total for e in exps]


def random_scores(profile: dict) -> dict:
    """
    Generate one row of scores. `profile` biases certain categories upward
    so each user looks different across the week.
    """
    raw = [
        random.gauss(profile.get("neutral",    0.5), 0.3),
        random.gauss(profile.get("humor",      0.2), 0.3),
        random.gauss(profile.get("stress",     0.3), 0.4),
        random.gauss(profile.get("burnout",    0.3), 0.4),
        random.gauss(profile.get("depression", 0.2), 0.3),
        random.gauss(profile.get("harassment", 0.1), 0.2),
        random.gauss(profile.get("suicidal",   0.05), 0.15),
    ]
    probs = softmax(raw)
    peak_idx = probs.index(max(probs))
    predicted_category = CATEGORIES[peak_idx]
    # severity: higher scores for risk categories get higher severity
    max_score = max(probs)
    if max_score < 0.35:
        severity = 0
    elif max_score < 0.55:
        severity = 1
    elif max_score < 0.75:
        severity = 2
    else:
        severity = 3

    return {
        "neutral_score":           round(probs[0], 6),
        "humor_sarcasm_score":     round(probs[1], 6),
        "stress_score":            round(probs[2], 6),
        "burnout_score":           round(probs[3], 6),
        "depression_score":        round(probs[4], 6),
        "harassment_score":        round(probs[5], 6),
        "suicidal_ideation_score": round(probs[6], 6),
        "predicted_category":      predicted_category,
        "predicted_severity":      severity,
    }


def random_profile() -> dict:
    """Each user gets a fixed bias profile so their trends are consistent."""
    style = random.choice(["burned_out", "stressed", "depressed", "harassed", "healthy"])
    base = {"neutral": 0.5, "humor": 0.2, "stress": 0.2,
            "burnout": 0.2, "depression": 0.15, "harassment": 0.1, "suicidal": 0.05}
    if style == "burned_out":
        base.update({"burnout": 0.8, "stress": 0.6, "neutral": 0.2})
    elif style == "stressed":
        base.update({"stress": 0.9, "burnout": 0.4, "neutral": 0.2})
    elif style == "depressed":
        base.update({"depression": 0.7, "burnout": 0.4, "neutral": 0.2})
    elif style == "harassed":
        base.update({"harassment": 0.6, "stress": 0.5, "neutral": 0.2})
    # "healthy" keeps defaults
    return base


SOURCES = ["slack", "gmail"]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python seed_incidents.py <company_id>")
        sys.exit(1)

    company_id = int(sys.argv[1])
    dsn = build_dsn()

    print(f"Connecting to DB...")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:

            # 1. Verify company exists
            cur.execute("SELECT name FROM companies WHERE company_id = %s", (company_id,))
            row = cur.fetchone()
            if not row:
                print(f"ERROR: company_id={company_id} not found.")
                sys.exit(1)
            print(f"Company: {row[0]}")

            # 2. Fetch active users
            cur.execute(
                "SELECT user_id FROM users WHERE company_id = %s AND status = 'active' AND deleted_at IS NULL",
                (company_id,),
            )
            users = [str(r[0]) for r in cur.fetchall()]
            if not users:
                print("ERROR: No active users found for this company.")
                sys.exit(1)
            print(f"Found {len(users)} active user(s).")

            # 3. Assign each user a stable random profile
            random.seed(company_id)  # reproducible profiles per company
            profiles = {uid: random_profile() for uid in users}
            random.seed()  # re-seed for daily score variation

            # 4. Generate data
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            days = [today - timedelta(days=d) for d in range(6, -1, -1)]  # oldest → newest

            incidents_inserted = 0
            scores_inserted = 0

            for day in days:
                for uid in users:
                    # Random time within working hours (8am–7pm)
                    sent_at = day + timedelta(
                        hours=random.randint(8, 19),
                        minutes=random.randint(0, 59),
                    )
                    message_id = str(uuid.uuid4())
                    source = random.choice(SOURCES)
                    content_raw = json.dumps({"text": "[seeded]", "seed": True})

                    # Insert message_incident
                    cur.execute(
                        """
                        INSERT INTO message_incidents
                            (message_id, company_id, user_id, source, sent_at, content_raw)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (message_id, company_id, uid, source, sent_at, content_raw),
                    )
                    incidents_inserted += cur.rowcount

                    # Insert incident_scores
                    scores = random_scores(profiles[uid])
                    cur.execute(
                        """
                        INSERT INTO incident_scores
                            (message_id,
                             neutral_score, humor_sarcasm_score, stress_score,
                             burnout_score, depression_score, harassment_score,
                             suicidal_ideation_score,
                             predicted_category, predicted_severity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            message_id,
                            scores["neutral_score"],
                            scores["humor_sarcasm_score"],
                            scores["stress_score"],
                            scores["burnout_score"],
                            scores["depression_score"],
                            scores["harassment_score"],
                            scores["suicidal_ideation_score"],
                            scores["predicted_category"],
                            scores["predicted_severity"],
                        ),
                    )
                    scores_inserted += cur.rowcount

            conn.commit()
            print(f"Done. Inserted {incidents_inserted} incidents, {scores_inserted} score rows.")
            print(f"Seeded {len(users)} users × 7 days = {len(users) * 7} rows each.")


if __name__ == "__main__":
    main()
