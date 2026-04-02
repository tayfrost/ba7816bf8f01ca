# AI Service

Mental health risk assessment agent using LangGraph.

## Structure

- **agent.py** - FastAPI app exposing the LangGraph agent
- **prompts/** - Versioned system prompts for mental health assessment
- **schema/** - Pydantic schemas for state and output validation
- **services/** - Prompt loading and MCP integration services
- **tests/** - Test suite for all components

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn agent:app --host 0.0.0.0 --port 8001
```

## Docker

```bash
docker-compose up ai_service
```

## Test

```bash
pytest tests/
```
