# SentinelAI Knowledge Graph

Evidence-based workplace mental health knowledge graph for the SentinelAI wellness agent. All advice is anchored to **92 peer-reviewed papers** with verifiable DOIs from JAMA, Cochrane, Annals of Internal Medicine, BJSM, PMC, Frontiers, and JMIR.

## Graph Schema

```
(Topic) <-[:COVERS]- (Paper) <-[:SOURCED_FROM]- (Advice) -[:USES_TECHNIQUE]-> (Technique) -[:ADDRESSES]-> (Topic)
```

Closed-loop ontology: every output traces back to a verified clinical source. See `docs/GRAPH_SCHEMA.md` for the full visual schema.

| Entity | Count | Description |
|--------|-------|-------------|
| Papers | 92 | DOI-verified research (10,000+ combined citations) |
| Advice Items | 368 | Actionable, confidence-scored interventions |
| Topics | 24 | Workplace mental health concern categories |
| Techniques | 37 | Evidence-based intervention methods |
| Tests | 63 | All passing (data integrity + agent + keywords) |

## Project Structure

```
knowledge-graph/
├── data/
│   └── papers.json              # Core dataset: 92 papers, 368 advice items
├── src/
│   ├── agent_integration.py     # NLP concern detection + graph query engine
│   ├── api.py                   # FastAPI REST wrapper (5 endpoints)
│   └── build_graph.py           # Neo4j Cypher generator
├── tests/
│   └── test_knowledge_graph.py  # 63 pytest tests
├── docs/
│   ├── GRAPH_SCHEMA.md          # Schema documentation
│   └── graph_schema.html        # Interactive schema visualisation
├── scripts/
│   ├── deploy.sh                # One-command deployment
│   ├── import.cypher            # Generated Neo4j import script
│   └── sample_queries.cypher    # Example Cypher queries
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

### JSON Fallback (no Neo4j required)

```python
from src.agent_integration import WellnessAgent

agent = WellnessAgent()
result = agent.get_advice("I'm feeling burned out and can't sleep")
print(agent.format_response(result))
```

### With Neo4j + API

```bash
docker-compose up -d
python src/build_graph.py --neo4j
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/advice` | Get ranked advice for user concern |
| GET | `/topics` | List all 24 topics |
| GET | `/techniques/{topic_id}` | Techniques for a topic |
| GET | `/stats` | Graph statistics |
| GET | `/health` | Service health check |

## Running Tests

```bash
cd knowledge-graph
python -m pytest tests/ -v
```

## Key Sources

| Journal | Papers |
|---------|--------|
| JAMA Network Open / Internal Medicine | 3 |
| Cochrane Database of Systematic Reviews | 2 |
| Annals of Internal Medicine | 1 |
| Cell Reports Medicine | 1 |
| British Journal of Sports Medicine | 2 |
| Journal of Medical Internet Research | 4 |
| Frontiers (Psychology, Psychiatry, Sleep) | 10+ |
| PMC / PLoS ONE | 15+ |

## Contributors

- Vishal Thakwani (k24059655)
