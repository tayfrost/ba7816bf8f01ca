"""MCP tool definitions for the SentinelAI Knowledge Graph server."""

from mcp.server.fastmcp import FastMCP

from sentinelai_kg.config import CRISIS_KEYWORDS, DISCLAIMER, MAX_INPUT_LENGTH
from sentinelai_kg.concerns import detect_concerns
from sentinelai_kg.data import get_dataset
from sentinelai_kg.formatting import clamp_results, format_recommendation

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
def get_recommendation(diagnosis: str, max_results: int = 5) -> dict:
    """Get ranked evidence-based recommendations for a mental health diagnosis or concern.

    PRIMARY TOOL. Given free-text describing a patient's symptoms, diagnosis, or
    workplace concern, detects relevant topics, queries the knowledge graph, and
    returns confidence-ranked advice with DOI-verified citations.

    If this returns 0 results, do NOT guess. Call list_topics to see available
    categories, then call get_recommendation_by_topic with the closest match.

    Args:
        diagnosis: Free-text description of the diagnosis, symptoms, or concern.
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with detected concerns, ranked advice items with citations, and disclaimer.
    """
    crisis_check = triage_crisis_risk(diagnosis)
    if crisis_check.get("crisis_detected"):
        return crisis_check

    diagnosis = diagnosis[:MAX_INPUT_LENGTH]
    max_results = clamp_results(max_results)
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
        "recommendations": [format_recommendation(r) for r in top],
        "total_matching": len(scored),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def get_recommendation_by_topic(topic_id: str, max_results: int = 5) -> dict:
    """Get recommendations for a specific topic ID from the knowledge graph.

    Use list_topics first to see available topic IDs, then query directly by ID
    for precise results without relying on keyword detection.

    Args:
        topic_id: Exact topic ID (e.g. "burnout", "anxiety", "sleep_issues").
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with the topic info, ranked advice items with citations, and disclaimer.
    """
    max_results = clamp_results(max_results)

    if topic_id not in get_dataset()["topics"]:
        return {"error": f"Unknown topic_id '{topic_id}'", "valid_topic_ids": list(get_dataset()["topics"].keys())}

    topic_info = get_dataset()["topics"][topic_id]
    matching = [a for a in get_dataset()["advice"] if topic_id in a["advice_topics"]]
    top = matching[:max_results]

    return {
        "topic": topic_info,
        "recommendations": [format_recommendation(r) for r in top],
        "total_matching": len(matching),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def get_recommendation_by_technique(technique_id: str, max_results: int = 5) -> dict:
    """Get recommendations that use a specific therapeutic technique.

    Args:
        technique_id: Technique ID (e.g. "cbt_restructuring", "mindfulness_meditation").
                      Use list_techniques to see all valid IDs.
        max_results: Maximum number of advice items to return (default 5, max 20)

    Returns:
        Dict with technique info, ranked advice items with citations, and disclaimer.
    """
    max_results = clamp_results(max_results)

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
        "recommendations": [format_recommendation(r) for r in top],
        "total_matching": len(matching),
        "returned": len(top),
        "disclaimer": DISCLAIMER,
    }


@mcp.tool()
def list_topics() -> dict:
    """List all 24 mental health topics available in the knowledge graph.

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
    """Search research papers by keyword, topic, or technique.

    At least one of query, topic_id, or technique_id must be provided.

    Args:
        query: Free-text search (matches title, advice text, and authors)
        topic_id: Filter by topic ID
        technique_id: Filter by technique ID
        min_citations: Minimum citation count filter (default 0)
        max_results: Maximum papers to return (default 10, max 30)

    Returns:
        Dict with matching papers and total count.
    """
    max_results = clamp_results(max_results, ceiling=30)

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
            advice_match = any(query_lower in a["text"].lower() for a in paper["advice"])
            author_match = any(query_lower in auth.lower() for auth in paper["authors"])
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
    """Get full details of a specific research paper including all advice items.

    Args:
        paper_id: Paper ID (e.g. "paper_001"). Use search_papers to find IDs.

    Returns:
        Dict with complete paper info and all advice items.
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
        Dict with counts, top journals, top-cited papers, and advice distribution.
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
