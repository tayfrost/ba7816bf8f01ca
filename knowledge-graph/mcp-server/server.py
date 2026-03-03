"""
SentinelAI Knowledge Graph MCP Server
Exposes the evidence-based mental health knowledge graph as MCP tools
for AI agents to query recommendations given a diagnosis.

Transport: SSE (Server-Sent Events) — connect at http://<host>:<port>/sse
"""

import json
import logging
import os
import re
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sentinelai-kg-mcp")

HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "")
HF_DATASET_FILE = os.environ.get("HF_DATASET_FILE", "papers.json")

LOCAL_DATA_PATH = os.environ.get(
    "KG_DATA_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "papers.json"),
)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))


def _resolve_data_path() -> str:
    """Resolve dataset path: HuggingFace Hub if configured, otherwise local file."""
    if HF_DATASET_REPO:
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(
                repo_id=HF_DATASET_REPO,
                filename=HF_DATASET_FILE,
                repo_type="dataset",
            )
            logger.info("Loaded dataset from HuggingFace: %s", HF_DATASET_REPO)
            return path
        except Exception as exc:
            logger.warning("HF download failed (%s), falling back to local", exc)

    if os.path.exists(LOCAL_DATA_PATH):
        logger.info("Using local dataset: %s", LOCAL_DATA_PATH)
        return LOCAL_DATA_PATH

    raise FileNotFoundError(
        f"No dataset found. Set HF_DATASET_REPO or ensure {LOCAL_DATA_PATH} exists."
    )

DISCLAIMER = (
    "This advice is based on peer-reviewed research and is not a "
    "substitute for professional mental health support."
)

MAX_INPUT_LENGTH = 2000

CRISIS_KEYWORDS = re.compile(
    r"\b("
    r"suicid(?:e|al|ality)|kill\s*my\s*self|end\s*(?:my\s*life|it\s*all)|want\s*to\s*die|"
    r"self[\s-]*harm(?:ing)?|cut(?:ting)?\s*my\s*self|hurt(?:ing)?\s*my\s*self|don'?t\s*want\s*to\s*live|"
    r"no\s*reason\s*to\s*live|better\s*off\s*dead|take\s*my\s*(?:own\s*)?life|"
    r"overdos(?:e|ed|ing)|hang\s*my\s*self"
    r")\b",
    re.IGNORECASE,
)


_DATASET: dict | None = None


def _load_dataset(data_path: str) -> dict:
    with open(data_path, "r") as f:
        data = json.load(f)

    topic_index = {t["id"]: t for t in data["topics"]}
    technique_index = {t["id"]: t for t in data["techniques"]}

    advice_items = []
    for paper in data["papers"]:
        for adv in paper["advice"]:
            technique_topics = technique_index.get(adv["technique"], {}).get("topics", [])
            advice_items.append({
                "text": adv["text"],
                "confidence": adv["confidence"],
                "technique_id": adv["technique"],
                "technique_name": technique_index.get(adv["technique"], {}).get("name", adv["technique"]),
                "technique_description": technique_index.get(adv["technique"], {}).get("description", ""),
                "paper_id": paper["id"],
                "paper_title": paper["title"],
                "paper_doi": paper.get("doi", "N/A"),
                "paper_year": paper["year"],
                "paper_citations": paper["citations"],
                "paper_topics": paper["topics"],
                "advice_topics": technique_topics if technique_topics else paper["topics"],
            })
    advice_items.sort(key=lambda x: (x["confidence"], x["paper_citations"]), reverse=True)

    return {
        "raw": data,
        "topics": topic_index,
        "techniques": technique_index,
        "advice": advice_items,
        "papers": data["papers"],
        "metadata": data["metadata"],
    }


def get_dataset() -> dict:
    """Lazy-load dataset on first access. Fail-fast but import-safe for tests."""
    global _DATASET
    if _DATASET is None:
        data_path = _resolve_data_path()
        _DATASET = _load_dataset(data_path)
        logger.info(
            "Dataset loaded: %d papers, %d advice items",
            len(_DATASET["papers"]),
            len(_DATASET["advice"]),
        )
    return _DATASET

# Word-boundary regex version of topic keywords (improved over src/agent_integration.py
# which uses simple substring matching). Kept separate to avoid coupling to Neo4j imports
# and to provide stricter matching for the MCP server.
TOPIC_KEYWORDS = {
    "workplace_stress": [
        "stress",         "stressed", "stressing", "pressure", "overwhelmed", "overwhelming", "workload",
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
    return [tid for tid, regex in TOPIC_REGEXES.items() if regex.search(text)]


def _clamp_results(max_results: int, ceiling: int = 20) -> int:
    return max(1, min(max_results, ceiling))


def _format_recommendation(r: dict) -> dict:
    return {
        "advice": r["text"],
        "confidence": r["confidence"],
        "technique": r["technique_name"],
        "technique_id": r["technique_id"],
        "technique_description": r["technique_description"],
        "paper_title": r["paper_title"],
        "paper_id": r["paper_id"],
        "doi": r["paper_doi"],
        "citations": r["paper_citations"],
    }


mcp = FastMCP(
    "SentinelAI Knowledge Graph",
    instructions=(
        "MCP server for querying the SentinelAI evidence-based mental health knowledge graph. "
        "Contains 92 DOI-verified research papers, 368 advice items, 24 topics, and 37 techniques "
        "for workplace mental health. Use get_recommendation to find the best advice for a "
        "diagnosis or concern. All advice is backed by peer-reviewed research with DOI citations. "
        "CRITICAL: Always check triage_crisis_risk BEFORE get_recommendation if the user's message "
        "mentions self-harm, suicide, or severe distress. "
        "CRITICAL: You MUST include the medical disclaimer in your final response to the user: "
        "'This advice is based on peer-reviewed research and is not a substitute for professional "
        "mental health support.'"
    ),
)


@mcp.tool()
def triage_crisis_risk(text: str) -> dict:
    """Check if user input contains crisis or self-harm indicators.

    CALL THIS FIRST before get_recommendation if the user's message mentions
    self-harm, suicide, death, or severe distress. If crisis is detected,
    the AI agent MUST prioritize the crisis response over any other recommendations.

    Args:
        text: The user's raw message text to screen for crisis indicators.

    Returns:
        Dict with crisis_detected flag and, if positive, emergency resources
        and strict instructions for the AI agent.
    """
    text = text[:MAX_INPUT_LENGTH]

    if CRISIS_KEYWORDS.search(text):
        return {
            "crisis_detected": True,
            "severity": "HIGH",
            "action_required": "IMMEDIATE_ESCALATION",
            "agent_instructions": (
                "STOP all other processing. Do NOT recommend breathing exercises or "
                "general wellness advice. Express empathy, validate their feelings, "
                "and provide the crisis resources below. Encourage them to reach out "
                "to a professional immediately."
            ),
            "crisis_resources": [
                {"name": "Samaritans (UK)", "contact": "116 123", "available": "24/7"},
                {"name": "Crisis Text Line (UK)", "contact": "Text SHOUT to 85258", "available": "24/7"},
                {"name": "NHS Urgent Mental Health", "contact": "111 (press 2)", "available": "24/7"},
                {"name": "International Association for Suicide Prevention", "contact": "https://www.iasp.info/resources/Crisis_Centres/"},
            ],
            "disclaimer": (
                "This is an automated screening tool and cannot replace professional "
                "crisis assessment. Always err on the side of caution."
            ),
        }

    return {
        "crisis_detected": False,
        "note": "No crisis indicators detected. Proceed with get_recommendation.",
    }


@mcp.tool()
def get_recommendation(
    diagnosis: str,
    max_results: int = 5,
) -> dict:
    """Get ranked evidence-based recommendations for a mental health diagnosis or concern.

    PRIMARY TOOL. Given free-text describing a patient's symptoms, diagnosis, or
    workplace concern, detects relevant topics, queries the knowledge graph, and
    returns confidence-ranked advice with DOI-verified citations.

    If this returns 0 results, do NOT guess. Call list_topics to see available
    categories, then call get_recommendation_by_topic with the closest match.

    Args:
        diagnosis: Free-text description of the diagnosis, symptoms, or concern.
                   Examples: "burnout and insomnia", "employee reporting anxiety and panic attacks",
                   "workplace bullying leading to depression"
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with detected concerns, ranked advice items (each with text, confidence,
        source paper, DOI, citation count, technique, and technique description),
        and a medical disclaimer.
    """
    crisis_check = triage_crisis_risk(diagnosis)
    if crisis_check.get("crisis_detected"):
        return crisis_check

    diagnosis = diagnosis[:MAX_INPUT_LENGTH]
    max_results = _clamp_results(max_results)
    concerns = detect_concerns(diagnosis)

    if not concerns:
        return {
            "detected_concerns": [],
            "recommendations": [],
            "total_matching": 0,
            "returned": 0,
            "hint": (
                "No specific mental health topics detected from input. "
                "Ask the user for more specific symptoms, or call list_topics "
                "then get_recommendation_by_topic with the closest match. "
                "If user is in crisis, call triage_crisis_risk immediately."
            ),
            "disclaimer": DISCLAIMER,
        }

    scored = []
    for a in get_dataset()["advice"]:
        overlap = len(set(concerns) & set(a["advice_topics"]))
        if overlap > 0:
            scored.append((overlap, a["confidence"], a["paper_citations"], a))

    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    top = [x[3] for x in scored[:max_results]]

    concern_names = [get_dataset()["topics"].get(c, {}).get("name", c) for c in concerns]

    return {
        "detected_concerns": concerns,
        "detected_concern_names": concern_names,
        "recommendations": [_format_recommendation(r) for r in top],
        "total_matching": len(scored),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def get_recommendation_by_topic(
    topic_id: str,
    max_results: int = 5,
) -> dict:
    """Get recommendations for a specific topic ID from the knowledge graph.

    Use list_topics first to see available topic IDs, then query directly by ID
    for precise results without relying on keyword detection.

    Args:
        topic_id: Exact topic ID (e.g. "burnout", "anxiety", "sleep_issues").
                  Use list_topics to see all valid IDs.
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with the topic info, ranked advice items with citations, and disclaimer.
    """
    max_results = _clamp_results(max_results)

    if topic_id not in get_dataset()["topics"]:
        return {"error": f"Unknown topic_id '{topic_id}'", "valid_topic_ids": list(get_dataset()["topics"].keys())}

    topic_info = get_dataset()["topics"][topic_id]
    matching = [a for a in get_dataset()["advice"] if topic_id in a["advice_topics"]]
    top = matching[:max_results]

    return {
        "topic": topic_info,
        "recommendations": [_format_recommendation(r) for r in top],
        "total_matching": len(matching),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def get_recommendation_by_technique(
    technique_id: str,
    max_results: int = 5,
) -> dict:
    """Get recommendations that use a specific therapeutic technique.

    Use this when the agent wants to recommend a particular intervention approach
    (e.g. CBT, mindfulness meditation, behavioral activation).

    Args:
        technique_id: Technique ID (e.g. "cbt_restructuring", "mindfulness_meditation",
                      "behavioral_activation"). Use list_techniques to see all valid IDs.
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with technique info, ranked advice items with citations, and disclaimer.
    """
    max_results = _clamp_results(max_results)

    if technique_id not in get_dataset()["techniques"]:
        return {
            "error": f"Unknown technique_id '{technique_id}'",
            "valid_technique_ids": [
                {"id": k, "name": v["name"]} for k, v in get_dataset()["techniques"].items()
            ],
        }

    technique_info = get_dataset()["techniques"][technique_id]
    matching = [a for a in get_dataset()["advice"] if a["technique_id"] == technique_id]
    top = matching[:max_results]

    return {
        "technique": {"id": technique_id, "name": technique_info["name"], "addresses_topics": technique_info["topics"]},
        "recommendations": [_format_recommendation(r) for r in top],
        "total_matching": len(matching),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def list_topics() -> dict:
    """List all 24 mental health topics available in the knowledge graph.

    Returns topic IDs, names, and descriptions. Use these IDs with
    get_recommendation_by_topic or get_techniques_for_topic for precise queries.

    Returns:
        Dict with list of all topics (id, name, description) and count.
    """
    topics = [
        {"id": tid, "name": t["name"], "description": t["description"]}
        for tid, t in get_dataset()["topics"].items()
    ]
    return {"topics": topics, "count": len(topics)}


@mcp.tool()
def get_techniques_for_topic(topic_id: str) -> dict:
    """Get all evidence-based techniques that address a specific mental health topic.

    Args:
        topic_id: Topic ID (e.g. "burnout", "anxiety", "sleep_issues").
                  Use list_topics to see all valid IDs.

    Returns:
        Dict with topic info and list of techniques (id, name, description).
    """
    if topic_id not in get_dataset()["topics"]:
        return {"error": f"Unknown topic_id '{topic_id}'", "valid_topic_ids": list(get_dataset()["topics"].keys())}

    techniques = [
        {"id": tid, "name": t["name"], "description": t["description"]}
        for tid, t in get_dataset()["techniques"].items()
        if topic_id in t.get("topics", [])
    ]

    return {
        "topic": get_dataset()["topics"][topic_id],
        "techniques": techniques,
        "count": len(techniques),
    }


@mcp.tool()
def search_papers(
    query: str = "",
    topic_id: str = "",
    technique_id: str = "",
    min_citations: int = 0,
    max_results: int = 10,
) -> dict:
    """Search research papers in the knowledge graph by keyword, topic, or technique.

    At least one of query, topic_id, or technique_id must be provided.

    Args:
        query: Free-text search (matches against paper title, advice text, and authors)
        topic_id: Filter by topic ID (e.g. "burnout", "anxiety")
        technique_id: Filter by technique ID (e.g. "cbt_restructuring", "mindful_breathing")
        min_citations: Minimum citation count filter (default 0)
        max_results: Maximum papers to return (default 10, max 30)

    Returns:
        Dict with matching papers (id, title, authors, year, source, doi, citations,
        topics, advice_count) and total count.
    """
    max_results = _clamp_results(max_results, ceiling=30)

    if not query and not topic_id and not technique_id:
        return {"error": "Provide at least one of: query, topic_id, or technique_id"}

    results = []
    query_lower = query.lower()[:MAX_INPUT_LENGTH] if query else ""

    for paper in get_dataset()["papers"]:
        if paper["citations"] < min_citations:
            continue

        if topic_id and topic_id not in paper.get("topics", []):
            continue

        if technique_id:
            paper_techniques = {a["technique"] for a in paper["advice"]}
            if technique_id not in paper_techniques:
                continue

        if query_lower:
            title_match = query_lower in paper["title"].lower()
            advice_match = any(
                query_lower in a["text"].lower() for a in paper["advice"]
            )
            author_match = any(
                query_lower in auth.lower() for auth in paper["authors"]
            )
            if not (title_match or advice_match or author_match):
                continue

        results.append({
            "id": paper["id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "year": paper["year"],
            "source": paper["source"],
            "doi": paper.get("doi", "N/A"),
            "citations": paper["citations"],
            "topics": paper["topics"],
            "advice_count": len(paper["advice"]),
        })

    results.sort(key=lambda x: x["citations"], reverse=True)

    return {
        "papers": results[:max_results],
        "total_matching": len(results),
        "returned": min(max_results, len(results)),
    }


@mcp.tool()
def get_paper_details(paper_id: str) -> dict:
    """Get full details of a specific research paper including all its advice items.

    Args:
        paper_id: Paper ID (e.g. "paper_001"). Use search_papers to find IDs.

    Returns:
        Dict with complete paper info: title, authors, year, source, DOI,
        citations, topics, and all advice items with techniques and confidence.
    """
    paper = next(
        (p for p in get_dataset()["papers"] if p["id"] == paper_id), None
    )
    if not paper:
        return {
            "error": f"Paper '{paper_id}' not found",
            "hint": "Use search_papers to find valid paper IDs",
        }

    return {
        "id": paper["id"],
        "title": paper["title"],
        "authors": paper["authors"],
        "year": paper["year"],
        "source": paper["source"],
        "doi": paper.get("doi", "N/A"),
        "citations": paper["citations"],
        "topics": [
            {"id": tid, "name": get_dataset()["topics"].get(tid, {}).get("name", tid)}
            for tid in paper["topics"]
        ],
        "advice": [
            {
                "text": a["text"],
                "technique_id": a["technique"],
                "technique_name": get_dataset()["techniques"].get(a["technique"], {}).get("name", a["technique"]),
                "technique_description": get_dataset()["techniques"].get(a["technique"], {}).get("description", ""),
                "confidence": a["confidence"],
            }
            for a in paper["advice"]
        ],
        "advice_count": len(paper["advice"]),
    }


@mcp.tool()
def list_techniques() -> dict:
    """List all 37 evidence-based techniques in the knowledge graph.

    Returns technique IDs, names, descriptions, and which topics they address.
    Useful for understanding what intervention methods are available.

    Returns:
        Dict with list of all techniques and count.
    """
    techniques = [
        {"id": tid, "name": t["name"], "description": t["description"], "addresses_topics": t["topics"]}
        for tid, t in get_dataset()["techniques"].items()
    ]
    return {"techniques": techniques, "count": len(techniques)}


@mcp.tool()
def get_stats() -> dict:
    """Get overall statistics about the knowledge graph.

    Returns:
        Dict with counts of papers, advice items, topics, techniques,
        total citations, top journals, top-cited papers, and advice distribution by topic.
    """
    total_advice = len(get_dataset()["advice"])
    total_papers = len(get_dataset()["papers"])
    total_citations = sum(p["citations"] for p in get_dataset()["papers"])

    sources = {}
    for p in get_dataset()["papers"]:
        src = p.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1
    top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]

    sorted_papers = sorted(get_dataset()["papers"], key=lambda x: x["citations"], reverse=True)[:5]

    topic_counts = {}
    for adv in get_dataset()["advice"]:
        for t in adv["advice_topics"]:
            topic_counts[t] = topic_counts.get(t, 0) + 1

    year_range = [
        min(p["year"] for p in get_dataset()["papers"]),
        max(p["year"] for p in get_dataset()["papers"]),
    ]

    return {
        "papers": total_papers,
        "advice_items": total_advice,
        "topics": len(get_dataset()["topics"]),
        "techniques": len(get_dataset()["techniques"]),
        "total_citations": total_citations,
        "avg_advice_per_paper": round(total_advice / total_papers, 1),
        "year_range": year_range,
        "top_cited_papers": [
            {"title": p["title"][:80], "citations": p["citations"], "doi": p.get("doi", "N/A")}
            for p in sorted_papers
        ],
        "advice_by_topic": {
            get_dataset()["topics"].get(tid, {}).get("name", tid): count
            for tid, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        },
        "top_journals": [{"source": s, "papers": c} for s, c in top_sources],
        "version": get_dataset()["metadata"]["version"],
    }


if __name__ == "__main__":
    import uvicorn
    get_dataset()
    uvicorn.run(mcp.get_asgi_app(), host=MCP_HOST, port=MCP_PORT)
