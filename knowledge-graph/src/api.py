"""
SentinelAI Knowledge Graph REST API
FastAPI wrapper for evidence-based mental health advice.

Endpoints:
    POST /advice       - Get evidence-based advice for a concern
    GET  /topics       - List all mental health topics
    GET  /techniques   - Get techniques for a topic
    GET  /stats        - Knowledge graph statistics
    GET  /health       - Health check

Run:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_integration import WellnessAgent

app = FastAPI(
    title="SentinelAI Knowledge Graph API",
    description="Evidence-based mental health advice powered by research paper knowledge graph",
    version="1.0.0",
)

# Initialize agent (uses JSON fallback if Neo4j unavailable)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
agent = WellnessAgent(neo4j_uri=NEO4J_URI)


class AdviceRequest(BaseModel):
    text: str
    max_results: int = 5

    class Config:
        json_schema_extra = {
            "example": {
                "text": "I'm feeling stressed at work and can't sleep",
                "max_results": 5,
            }
        }


class AdviceResponse(BaseModel):
    concerns: list
    advice: list
    total_results: int
    disclaimer: str


@app.post("/advice", response_model=AdviceResponse)
async def get_advice(request: AdviceRequest):
    """Get evidence-based advice for a mental health concern."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    result = agent.get_advice(request.text, request.max_results)
    return result


@app.get("/topics")
async def get_topics():
    """List all available mental health topics."""
    return {"topics": agent.get_topics()}


@app.get("/techniques/{topic_id}")
async def get_techniques(topic_id: str):
    """Get techniques that address a specific topic."""
    techniques = agent.get_techniques_for_topic(topic_id)
    if not techniques:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
    return {"topic": topic_id, "techniques": techniques}


@app.get("/stats")
async def get_stats():
    """Return knowledge graph statistics."""
    return agent.get_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    stats = agent.get_stats()
    return {
        "status": "healthy",
        "neo4j_connected": agent.driver is not None,
        "papers_loaded": stats.get("papers", 0),
        "advice_items": stats.get("advice", 0),
    }


@app.on_event("shutdown")
def shutdown():
    agent.close()
