"""
SentinelAI Knowledge Graph Builder v3.0
Builds Neo4j graph from 92 DOI-verified clinical papers.
Generates Cypher import script for Neo4j ingestion.
"""

import json
import os
import sys
import argparse
from datetime import datetime

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

PAPERS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.json")
CYPHER_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "scripts", "import.cypher")


def load_dataset(path: str = PAPERS_PATH) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def generate_cypher(dataset: dict) -> str:
    lines = []
    lines.append("// ==============================================")
    lines.append("// SentinelAI Knowledge Graph v3.0 - Neo4j Import")
    lines.append(f"// Generated: {datetime.now().isoformat()}")
    lines.append(f"// Papers: {len(dataset['papers'])}")
    total_advice = sum(len(p['advice']) for p in dataset['papers'])
    lines.append(f"// Advice Items: {total_advice}")
    lines.append(f"// Sources: Verified DOIs from PMC, arXiv, Frontiers, BJSM, JMIR")
    lines.append("// ==============================================\n")

    lines.append("// --- Constraints & Indexes ---")
    lines.append("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE;")
    lines.append("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE;")
    lines.append("CREATE CONSTRAINT IF NOT EXISTS FOR (tc:Technique) REQUIRE tc.id IS UNIQUE;")
    lines.append("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Advice) REQUIRE a.id IS UNIQUE;")
    lines.append("CREATE INDEX IF NOT EXISTS FOR (a:Advice) ON (a.text);")
    lines.append("CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.citations);")
    lines.append("CREATE INDEX IF NOT EXISTS FOR (a:Advice) ON (a.confidence);")
    lines.append("")

    lines.append("// --- Topics ---")
    for topic in dataset["topics"]:
        escaped_name = topic["name"].replace("'", "\\'")
        escaped_desc = topic["description"].replace("'", "\\'")
        lines.append(
            f"MERGE (t:Topic {{id: '{topic['id']}'}}) "
            f"SET t.name = '{escaped_name}', "
            f"t.description = '{escaped_desc}';"
        )
    lines.append("")

    lines.append("// --- Techniques ---")
    for tech in dataset["techniques"]:
        escaped_name = tech["name"].replace("'", "\\'")
        lines.append(
            f"MERGE (tc:Technique {{id: '{tech['id']}'}}) "
            f"SET tc.name = '{escaped_name}';"
        )
    lines.append("")

    lines.append("// --- Technique-Topic Links ---")
    for tech in dataset["techniques"]:
        for topic_id in tech["topics"]:
            lines.append(
                f"MATCH (tc:Technique {{id: '{tech['id']}'}}), (t:Topic {{id: '{topic_id}'}}) "
                f"MERGE (tc)-[:ADDRESSES]->(t);"
            )
    lines.append("")

    lines.append("// --- Papers & Advice ---")
    advice_counter = 0
    for paper in dataset["papers"]:
        escaped_title = paper["title"].replace("'", "\\'")
        authors_str = ", ".join(paper["authors"]).replace("'", "\\'")
        doi = paper.get("doi", "N/A").replace("'", "\\'")
        lines.append(
            f"MERGE (p:Paper {{id: '{paper['id']}'}}) "
            f"SET p.title = '{escaped_title}', "
            f"p.authors = '{authors_str}', "
            f"p.year = {paper['year']}, "
            f"p.source = '{paper.get('source', '')}', "
            f"p.doi = '{doi}', "
            f"p.citations = {paper['citations']};"
        )

        for topic_id in paper["topics"]:
            lines.append(
                f"MATCH (p:Paper {{id: '{paper['id']}'}}), (t:Topic {{id: '{topic_id}'}}) "
                f"MERGE (p)-[:COVERS]->(t);"
            )

        for i, advice in enumerate(paper["advice"]):
            advice_id = f"advice_{advice_counter}"
            escaped_text = advice["text"].replace("'", "\\'")
            lines.append(
                f"MERGE (a:Advice {{id: '{advice_id}'}}) "
                f"SET a.text = '{escaped_text}', "
                f"a.confidence = {advice['confidence']};"
            )
            lines.append(
                f"MATCH (a:Advice {{id: '{advice_id}'}}), (p:Paper {{id: '{paper['id']}'}}) "
                f"MERGE (a)-[:SOURCED_FROM]->(p);"
            )
            lines.append(
                f"MATCH (a:Advice {{id: '{advice_id}'}}), (tc:Technique {{id: '{advice['technique']}'}}) "
                f"MERGE (a)-[:USES_TECHNIQUE]->(tc);"
            )
            advice_counter += 1

        lines.append("")

    lines.append(f"// Total: {advice_counter} advice nodes created")
    return "\n".join(lines)


def import_to_neo4j(cypher: str, uri: str = "bolt://localhost:7687",
                     user: str = "neo4j", password: str = "sentinelai2025"):
    if not HAS_NEO4J:
        print("ERROR: neo4j Python driver not installed. Run: pip install neo4j")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    statements = [s.strip() for s in cypher.split(";") if s.strip() and not s.strip().startswith("//")]

    print(f"Importing {len(statements)} Cypher statements to {uri}...")
    with driver.session() as session:
        for i, stmt in enumerate(statements):
            try:
                session.run(stmt)
            except Exception as e:
                print(f"  WARNING on statement {i}: {e}")
        print(f"  Done. {len(statements)} statements executed.")

    driver.close()


def main():
    parser = argparse.ArgumentParser(description="Build SentinelAI Knowledge Graph v2")
    parser.add_argument("--neo4j", action="store_true", help="Import to running Neo4j instance")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-pass", default="sentinelai2025")
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()

    print("Loading dataset...")
    dataset = load_dataset()
    print(f"  Papers: {len(dataset['papers'])}")
    print(f"  Topics: {len(dataset['topics'])}")
    print(f"  Techniques: {len(dataset['techniques'])}")

    total_advice = sum(len(p["advice"]) for p in dataset["papers"])
    print(f"  Advice items: {total_advice}")

    print("\nGenerating Cypher import script...")
    cypher = generate_cypher(dataset)

    with open(CYPHER_OUTPUT, "w") as f:
        f.write(cypher)
    print(f"  Saved to: {CYPHER_OUTPUT}")

    if args.neo4j and not args.export_only:
        import_to_neo4j(cypher, args.neo4j_uri, args.neo4j_user, args.neo4j_pass)

    print("\nDone!")


if __name__ == "__main__":
    main()
