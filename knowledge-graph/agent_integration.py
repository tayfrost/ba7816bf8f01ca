"""
SentinelAI Wellness Agent - Knowledge Graph Integration
Provides evidence-based mental health advice by querying
the research paper knowledge graph.

Works with Neo4j or falls back to JSON dataset.
"""

import json
import os
import re
from typing import Optional

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

PAPERS_PATH = os.path.join(os.path.dirname(__file__), "papers.json")

# Keywords for topic detection
TOPIC_KEYWORDS = {
    "workplace_stress": ["stress", "stressed", "pressure", "overwhelmed", "workload", "deadline", "overwork", "demanding"],
    "burnout": ["burnout", "burned out", "exhausted", "drained", "depleted", "tired of work", "no energy"],
    "anxiety": ["anxious", "anxiety", "nervous", "worried", "worry", "panic", "fear", "uneasy", "restless"],
    "depression": ["depressed", "depression", "sad", "hopeless", "empty", "no motivation", "worthless", "down"],
    "anger_management": ["angry", "anger", "furious", "irritated", "frustrated", "rage", "annoyed", "hostile"],
    "sleep_issues": ["sleep", "insomnia", "can't sleep", "tired", "fatigue", "restless nights", "wake up"],
    "work_life_balance": ["balance", "overwork", "boundaries", "personal time", "family time", "always working"],
    "social_isolation": ["lonely", "alone", "isolated", "disconnected", "no friends", "remote work lonely"],
    "emotional_regulation": ["emotions", "emotional", "can't control", "overwhelmed", "mood swings", "reactive"],
    "resilience": ["resilience", "bounce back", "tough time", "setback", "recovery", "cope", "adapt"],
    "mindfulness": ["mindful", "mindfulness", "present", "meditation", "awareness", "focus"],
    "cognitive_distortions": ["negative thoughts", "overthinking", "catastrophizing", "worst case", "ruminating", "rumination"],
    "interpersonal_conflict": ["conflict", "argument", "disagreement", "difficult colleague", "toxic", "confrontation"],
}


class WellnessAgent:
    """
    Evidence-based wellness agent powered by knowledge graph.
    Detects user concerns, queries the graph, and returns
    research-backed advice with paper citations.
    """

    def __init__(self, neo4j_uri: Optional[str] = None, neo4j_user: str = "neo4j",
                 neo4j_password: str = "sentinelai2025"):
        self.driver = None
        self.dataset = None

        # Try Neo4j first
        if neo4j_uri and HAS_NEO4J:
            try:
                self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                self.driver.verify_connectivity()
                print(f"Connected to Neo4j at {neo4j_uri}")
            except Exception as e:
                print(f"Neo4j unavailable ({e}), falling back to JSON")
                self.driver = None

        # Fallback to JSON
        if not self.driver:
            self._load_json()

    def _load_json(self):
        """Load dataset from JSON file."""
        with open(PAPERS_PATH, "r") as f:
            self.dataset = json.load(f)
        print(f"Loaded JSON dataset: {len(self.dataset['papers'])} papers")

    def detect_concerns(self, text: str) -> list[str]:
        """Detect mental health topics from user input text."""
        text_lower = text.lower()
        detected = []
        for topic_id, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    detected.append(topic_id)
                    break
        return detected if detected else ["workplace_stress"]  # Default

    def get_advice(self, text: str, max_results: int = 5) -> dict:
        """Get evidence-based advice for user's concern."""
        concerns = self.detect_concerns(text)

        if self.driver:
            return self._query_neo4j(concerns, max_results)
        else:
            return self._query_json(concerns, max_results)

    def _query_neo4j(self, concerns: list[str], max_results: int) -> dict:
        """Query Neo4j knowledge graph."""
        query = """
        MATCH (a:Advice)-[:SOURCED_FROM]->(p:Paper)-[:COVERS]->(t:Topic)
        WHERE t.id IN $topics
        OPTIONAL MATCH (a)-[:USES_TECHNIQUE]->(tc:Technique)
        RETURN a.text AS advice, a.confidence AS confidence,
               p.title AS paper, p.arxiv_id AS arxiv_id, p.citations AS citations,
               tc.name AS technique, t.id AS topic
        ORDER BY a.confidence DESC, p.citations DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, topics=concerns, limit=max_results)
            advice_list = []
            for record in result:
                advice_list.append({
                    "advice": record["advice"],
                    "confidence": record["confidence"],
                    "paper": record["paper"],
                    "arxiv_id": record["arxiv_id"],
                    "citations": record["citations"],
                    "technique": record["technique"],
                    "topic": record["topic"],
                })

        return {
            "concerns": concerns,
            "advice": advice_list,
            "total_results": len(advice_list),
            "disclaimer": "This advice is based on research papers and is not a substitute for professional mental health support.",
        }

    def _query_json(self, concerns: list[str], max_results: int) -> dict:
        """Query JSON dataset (fallback when Neo4j unavailable)."""
        advice_list = []

        for paper in self.dataset["papers"]:
            # Check if paper covers any detected concern
            paper_topics = set(paper.get("topics", []))
            matching_topics = paper_topics.intersection(set(concerns))

            if matching_topics:
                for adv in paper["advice"]:
                    advice_list.append({
                        "advice": adv["text"],
                        "confidence": adv["confidence"],
                        "paper": paper["title"],
                        "arxiv_id": paper.get("arxiv_id", ""),
                        "citations": paper["citations"],
                        "technique": adv["technique"],
                        "topic": list(matching_topics)[0],
                    })

        # Sort by confidence and citations
        advice_list.sort(key=lambda x: (x["confidence"], x["citations"]), reverse=True)

        return {
            "concerns": concerns,
            "advice": advice_list[:max_results],
            "total_results": min(max_results, len(advice_list)),
            "disclaimer": "This advice is based on research papers and is not a substitute for professional mental health support.",
        }

    def get_topics(self) -> list[dict]:
        """List all available topics."""
        if self.driver:
            with self.driver.session() as session:
                result = session.run("MATCH (t:Topic) RETURN t.id AS id, t.name AS name, t.description AS description")
                return [dict(r) for r in result]
        else:
            return self.dataset.get("topics", [])

    def get_techniques_for_topic(self, topic_id: str) -> list[dict]:
        """Get techniques that address a specific topic."""
        if self.driver:
            query = """
            MATCH (tc:Technique)-[:ADDRESSES]->(t:Topic {id: $topic_id})
            RETURN tc.id AS id, tc.name AS name
            """
            with self.driver.session() as session:
                result = session.run(query, topic_id=topic_id)
                return [dict(r) for r in result]
        else:
            techniques = []
            for tech in self.dataset.get("techniques", []):
                if topic_id in tech.get("topics", []):
                    techniques.append({"id": tech["id"], "name": tech["name"]})
            return techniques

    def get_stats(self) -> dict:
        """Return knowledge graph statistics."""
        if self.driver:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Paper) WITH count(p) AS papers
                    MATCH (a:Advice) WITH papers, count(a) AS advice
                    MATCH (t:Topic) WITH papers, advice, count(t) AS topics
                    MATCH (tc:Technique) WITH papers, advice, topics, count(tc) AS techniques
                    RETURN papers, advice, topics, techniques
                """)
                record = result.single()
                return dict(record) if record else {}
        else:
            return {
                "papers": len(self.dataset.get("papers", [])),
                "advice": sum(len(p["advice"]) for p in self.dataset.get("papers", [])),
                "topics": len(self.dataset.get("topics", [])),
                "techniques": len(self.dataset.get("techniques", [])),
            }

    def format_response(self, result: dict) -> str:
        """Format advice result into human-readable text."""
        lines = []
        lines.append(f"Detected concerns: {', '.join(result['concerns'])}\n")

        for i, adv in enumerate(result["advice"], 1):
            lines.append(f"{i}. {adv['advice']}")
            lines.append(f"   Technique: {adv['technique']}")
            lines.append(f"   Source: {adv['paper']} (arXiv:{adv['arxiv_id']}, {adv['citations']} citations)")
            lines.append(f"   Confidence: {adv['confidence']:.0%}")
            lines.append("")

        lines.append(f"\n{result['disclaimer']}")
        return "\n".join(lines)

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()


# CLI usage
if __name__ == "__main__":
    import sys

    agent = WellnessAgent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "I'm feeling stressed at work and can't sleep properly"

    print(f"Query: {query}\n")
    result = agent.get_advice(query, max_results=5)
    print(agent.format_response(result))
    agent.close()
