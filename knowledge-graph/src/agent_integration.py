"""
SentinelAI Wellness Agent - Knowledge Graph Integration v3.0
Evidence-based mental health advice backed by 92 DOI-verified peer-reviewed papers.
Works with Neo4j or falls back to JSON dataset.
"""

import json
import os
from typing import Optional

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

PAPERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.json")

# Maps detected concern keywords to actual topic IDs in the knowledge graph
TOPIC_KEYWORDS = {
    "workplace_stress": [
        "stress", "stressed", "pressure", "overwhelmed", "workload", "deadline",
        "overwork", "demanding", "hectic", "stressful", "under pressure"
    ],
    "burnout": [
        "burnout", "burned out", "exhausted", "drained", "depleted", "tired of work",
        "no energy", "can't cope", "running on empty", "worn out", "cynical about work"
    ],
    "anxiety": [
        "anxious", "anxiety", "nervous", "worried", "worry", "panic", "fear",
        "uneasy", "restless", "dread", "on edge", "apprehensive"
    ],
    "depression": [
        "depressed", "depression", "sad", "hopeless", "empty", "no motivation",
        "worthless", "down", "unmotivated", "failure", "lost interest"
    ],
    "anger_management": [
        "angry", "anger", "furious", "irritated", "frustrated", "rage", "annoyed",
        "hostile", "mad", "snap", "lose my temper", "resentful"
    ],
    "sleep_issues": [
        "sleep", "insomnia", "can't sleep", "tired", "fatigue", "restless nights",
        "wake up", "shift work", "exhaustion", "not sleeping"
    ],
    "work_life_balance": [
        "balance", "overwork", "boundaries", "personal time", "family time",
        "always working", "never off", "weekends", "after hours", "disconnect"
    ],
    "social_isolation": [
        "lonely", "alone", "isolated", "disconnected", "no friends",
        "remote work lonely", "detached", "nobody to talk to", "left out"
    ],
    "emotional_regulation": [
        "emotions", "emotional", "can't control", "mood swings", "reactive",
        "outburst", "overwhelmed feelings", "overreact", "impulsive"
    ],
    "resilience": [
        "resilience", "bounce back", "tough time", "setback", "recovery",
        "cope", "adapt", "get through this", "overcome", "persevere"
    ],
    "mindfulness": [
        "mindful", "mindfulness", "present", "meditation", "awareness",
        "focus", "centered", "grounded", "calm", "attention"
    ],
    "cognitive_distortions": [
        "negative thoughts", "overthinking", "catastrophizing", "worst case",
        "ruminating", "rumination", "spiraling", "all or nothing"
    ],
    "interpersonal_conflict": [
        "conflict", "argument", "disagreement", "difficult colleague", "toxic",
        "confrontation", "fight", "dispute", "manager", "difficult conversation"
    ],
    "self_compassion": [
        "self-criticism", "too hard on myself", "not good enough", "self-blame",
        "beating myself up", "harsh on myself", "self-doubt", "inner critic"
    ],
    "perfectionism": [
        "perfect", "perfectionist", "mistake", "flaw", "impossible standards",
        "never satisfied", "high standards", "fear of failure"
    ],
    "time_poverty": [
        "no time", "busy", "swamped", "schedule", "late", "behind",
        "too much to do", "overwhelmed with tasks", "time management"
    ],
    "workplace_bullying": [
        "bullying", "bullied", "bully", "harassment", "harassed", "intimidation",
        "threatened", "mobbing", "picked on", "targeted", "abused at work"
    ],
    "digital_interventions": [
        "app", "online program", "digital", "ehealth", "web-based",
        "self-help app", "computerized", "digital therapy"
    ],
    "act_values": [
        "stuck", "rigid", "avoidance", "acceptance", "values",
        "committed action", "defusion", "act therapy", "psychological flexibility"
    ],
    "occupational_health": [
        "disengaged", "meaningless", "bored at work", "no purpose",
        "job crafting", "engagement", "meaningful work", "prevention"
    ],
    "organizational_culture": [
        "management support", "leadership", "culture", "organizational change",
        "team support", "workplace policy", "manager help", "eap", "psychological safety"
    ],
    "physical_activity": [
        "exercise", "workout", "physical activity", "gym", "running",
        "walking", "movement", "sedentary", "fitness", "active"
    ],
    "expressive_writing": [
        "journal", "journaling", "write about feelings", "expressive writing",
        "diary", "reflection", "writing therapy"
    ],
    "biofeedback": [
        "biofeedback", "hrv", "heart rate variability", "resonance breathing",
        "physiological", "wearable", "breathing exercise"
    ],
}


class WellnessAgent:
    """
    Evidence-based wellness agent powered by knowledge graph.
    Detects user concerns, queries the graph, and returns
    research-backed advice with DOI citations.
    """

    def __init__(self, neo4j_uri: Optional[str] = None, neo4j_user: str = "neo4j",
                 neo4j_password: str = "sentinelai2025"):
        self.driver = None
        self.dataset = None

        if neo4j_uri and HAS_NEO4J:
            try:
                self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                self.driver.verify_connectivity()
            except Exception:
                self.driver = None

        if not self.driver:
            self._load_json()

    def _load_json(self):
        with open(PAPERS_PATH, "r") as f:
            self.dataset = json.load(f)

    def detect_concerns(self, text: str) -> list[str]:
        text_lower = text.lower()
        detected = []
        for topic_id, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    detected.append(topic_id)
                    break
        return detected if detected else ["workplace_stress"]

    def get_advice(self, text: str, max_results: int = 5) -> dict:
        concerns = self.detect_concerns(text)
        if self.driver:
            return self._query_neo4j(concerns, max_results)
        return self._query_json(concerns, max_results)

    def _query_neo4j(self, concerns: list[str], max_results: int) -> dict:
        query = """
        MATCH (p:Paper)-[:COVERS]->(t:Topic)
        WHERE t.id IN $topics
        MATCH (p)-[:PROVIDES]->(a:Advice)-[:USES]->(tc:Technique)
        RETURN a.text AS advice, a.confidence AS confidence,
               p.title AS paper, p.doi AS doi, p.citations AS citations,
               tc.name AS technique, t.id AS topic
        ORDER BY a.confidence DESC, p.citations DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, topics=concerns, limit=max_results)
            advice_list = [dict(r) for r in result]
        return {
            "concerns": concerns, "advice": advice_list,
            "total_results": len(advice_list),
            "disclaimer": "This advice is based on peer-reviewed research and is not a substitute for professional mental health support.",
        }

    def _query_json(self, concerns: list[str], max_results: int) -> dict:
        advice_list = []
        for paper in self.dataset["papers"]:
            matching = set(paper.get("topics", [])) & set(concerns)
            if matching:
                for adv in paper["advice"]:
                    advice_list.append({
                        "advice": adv["text"], "confidence": adv["confidence"],
                        "paper": paper["title"], "doi": paper.get("doi", "N/A"),
                        "citations": paper["citations"], "technique": adv["technique"],
                        "topic": list(matching)[0],
                    })
        advice_list.sort(key=lambda x: (x["confidence"], x["citations"]), reverse=True)
        return {
            "concerns": concerns, "advice": advice_list[:max_results],
            "total_results": min(max_results, len(advice_list)),
            "disclaimer": "This advice is based on peer-reviewed research and is not a substitute for professional mental health support.",
        }

    def get_topics(self) -> list[dict]:
        if self.driver:
            with self.driver.session() as session:
                result = session.run("MATCH (t:Topic) RETURN t.id AS id, t.name AS name, t.description AS description")
                return [dict(r) for r in result]
        return self.dataset.get("topics", [])

    def get_techniques_for_topic(self, topic_id: str) -> list[dict]:
        if self.driver:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (tc:Technique)-[:ADDRESSES]->(t:Topic {id: $tid}) RETURN tc.id AS id, tc.name AS name",
                    tid=topic_id)
                return [dict(r) for r in result]
        return [{"id": t["id"], "name": t["name"]}
                for t in self.dataset.get("techniques", []) if topic_id in t.get("topics", [])]

    def get_stats(self) -> dict:
        if self.driver:
            with self.driver.session() as session:
                r = session.run("""
                    MATCH (p:Paper) WITH count(p) AS papers
                    MATCH (a:Advice) WITH papers, count(a) AS advice
                    MATCH (t:Topic) WITH papers, advice, count(t) AS topics
                    MATCH (tc:Technique) WITH papers, advice, topics, count(tc) AS techniques
                    RETURN papers, advice, topics, techniques
                """).single()
                return dict(r) if r else {}
        return {
            "papers": len(self.dataset.get("papers", [])),
            "advice": sum(len(p["advice"]) for p in self.dataset.get("papers", [])),
            "topics": len(self.dataset.get("topics", [])),
            "techniques": len(self.dataset.get("techniques", [])),
        }

    def format_response(self, result: dict) -> str:
        lines = [f"Detected concerns: {', '.join(result['concerns'])}\n"]
        for i, adv in enumerate(result["advice"], 1):
            doi_str = f"DOI: {adv['doi']}" if adv.get('doi') and adv['doi'] != 'N/A' else ""
            lines.append(f"{i}. {adv['advice']}")
            lines.append(f"   Technique: {adv['technique']}")
            lines.append(f"   Source: {adv['paper']} ({adv['citations']} citations) {doi_str}")
            lines.append(f"   Confidence: {adv['confidence']:.0%}\n")
        lines.append(result['disclaimer'])
        return "\n".join(lines)

    def close(self):
        if self.driver:
            self.driver.close()


if __name__ == "__main__":
    import sys
    agent = WellnessAgent()
    query = " ".join(sys.argv[1:]) if len(sys.argv[1:]) else "I'm feeling stressed at work and can't sleep"
    print(f"Query: {query}\n")
    result = agent.get_advice(query, max_results=5)
    print(agent.format_response(result))
    agent.close()
