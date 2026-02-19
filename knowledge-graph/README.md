# SentinelAI Knowledge Graph

Research paper knowledge graph for the SentinelAI mental health wellness agent. Provides evidence-based, citation-backed advice for workplace mental health concerns.

## Overview

The knowledge graph connects **30 research papers** from arXiv to **114 actionable advice items** across **13 mental health topics** and **17 evidence-based techniques**.

### Graph Schema

```
(Topic) <-[:COVERS]- (Paper) <-[:SOURCED_FROM]- (Advice) -[:USES_TECHNIQUE]-> (Technique)
                                                          (Technique) -[:ADDRESSES]-> (Topic)
```

### How It Works

1. **Concern Detection**: NLP keyword matching maps user input to topic IDs
2. **Graph Query**: Cypher queries retrieve advice nodes linked to detected topics
3. **Ranking**: Results sorted by confidence score and paper citation count
4. **Response**: Formatted with advice text, source paper, and technique tags

## Files

```
knowledge-graph/
├── README.md                  # This file
├── papers.json                # Research papers dataset (30 papers, 114 advice items)
├── build_graph.py             # Neo4j graph builder + Cypher exporter
├── import.cypher              # Generated Cypher import script (run build_graph.py first)
├── agent_integration.py       # Agent ↔ knowledge graph interface
├── api.py                     # FastAPI REST wrapper
├── test_knowledge_graph.py    # Unit tests (45 tests)
├── sample_queries.cypher      # 10 example Cypher queries
├── docker-compose.yml         # Neo4j container config
├── deploy.sh                  # Start → Import → Export → Test
└── requirements.txt           # Python dependencies
```

## Quick Start

### Option 1: With Docker (recommended)

```bash
# Start Neo4j
docker-compose up -d

# Build graph and generate Cypher
pip install -r requirements.txt
python build_graph.py

# Import to Neo4j
cat import.cypher | docker exec -i sentinelai-neo4j cypher-shell -u neo4j -p sentinelai2025

# Run tests
python -m pytest test_knowledge_graph.py -v
```

### Option 2: JSON Fallback (no Neo4j required)

The agent works without Neo4j using the JSON dataset directly:

```python
from agent_integration import WellnessAgent

agent = WellnessAgent()  # Auto-uses JSON fallback
result = agent.get_advice("I'm feeling stressed and can't sleep")
print(agent.format_response(result))
```

### Option 3: REST API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000

# Query
curl -X POST http://localhost:8000/advice \
  -H "Content-Type: application/json" \
  -d '{"text": "I feel burned out", "max_results": 3}'
```

### One-Command Deploy

```bash
chmod +x deploy.sh
./deploy.sh all
```

## Database Export

For deployment, the Neo4j volume can be exported and shared:

```bash
./deploy.sh export
# Creates knowledge-graph-db.tar.gz
```

Upload the tar.gz to a public file sharing service and add the link here.

## Topics Covered

| Topic | Description |
|-------|-------------|
| Workplace Stress | Work demands, deadlines, organizational pressure |
| Burnout | Chronic exhaustion, cynicism, reduced efficacy |
| Anxiety | Excessive worry, nervousness, performance anxiety |
| Depression | Low mood, hopelessness, loss of motivation |
| Anger Management | Difficulty regulating anger in professional settings |
| Sleep Issues | Insomnia, poor sleep quality, fatigue |
| Work-Life Balance | Boundary maintenance between work and personal life |
| Social Isolation | Loneliness, disconnection (esp. remote work) |
| Emotional Regulation | Managing emotional responses professionally |
| Resilience | Recovery from adversity and adaptation |
| Mindfulness | Present-moment awareness practices |
| Cognitive Distortions | Negative thinking patterns |
| Interpersonal Conflict | Workplace relationship difficulties |

## Techniques

Deep Breathing, Progressive Muscle Relaxation, Mindfulness Meditation, CBT Restructuring, Journaling, Time Management, Boundary Setting, Social Support, Physical Activity, Sleep Hygiene, Gratitude Practice, Assertiveness Training, Problem-Solving Therapy, Guided Visualization, Self-Compassion, Micro-Breaks, Emotional Labeling.

## Contributors

- Vishal Thakwani (k24059655) - Knowledge Graph Design & Implementation
