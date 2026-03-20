"""Mental health risk assessment agent with LangGraph workflow."""

import os
import asyncio
import logging
from typing import Literal, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from fastmcp import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.prompt_service import PromptService
from services.mcp_service import get_mcp_client
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore, BatchAgentOutput
from schema.request import AnalyzeRequest, BatchAnalyzeRequest

load_dotenv()

app = FastAPI(title="SentinelAI Mental Health Assessment")

# Initialize services
prompt_service = PromptService()

# Import state functions
from states.redactor_state import redactor
from states.assess_risk_state import assess_risk
from states.grade_message_state import grade_message
from states.generate_recommendations_state import generate_recommendations


def should_continue(state: AgentState) -> Literal["grade", "end"]:
    """Route based on risk assessment."""
    if state.get('is_confirmed_risk'):
        return "grade"
    return "end"


# Build LangGraph workflow
workflow = StateGraph(AgentState)

workflow.add_node("redactor", redactor)
workflow.add_node("assess_risk", assess_risk)
workflow.add_node("grade_message", grade_message)
workflow.add_node("generate_recommendations", generate_recommendations)

workflow.set_entry_point("redactor")
workflow.add_edge("redactor", "assess_risk")
workflow.add_conditional_edges(
    "assess_risk",
    should_continue,
    {
        "grade": "grade_message",
        "end": END
    }
)
workflow.add_edge("grade_message", "generate_recommendations")
workflow.add_edge("generate_recommendations", END)

agent = workflow.compile()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "SentinelAI"}


@app.post("/analyze", response_model=AgentOutput)
async def analyze_message(request: AnalyzeRequest, mcp_client: Client = Depends(get_mcp_client)):
    """Analyze a single message for mental health risks."""
    logger.info("="*80)
    logger.info(f"[API] New analyze request received")
    logger.info(f"[API] Message length: {len(request.message)} chars")
    logger.info("="*80)

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        return await _analyze_single(request.message, mcp_client)
    except Exception as e:
        logger.error(f"[API] Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def _analyze_single(message: str, mcp_client: Client) -> AgentOutput:
    """Run the agent workflow on a single message. Reused by both endpoints."""
    initial_state: AgentState = {"raw_message": message}
    result = await agent.ainvoke(
        initial_state,
        config={"configurable": {"mcp_client": mcp_client}},
    )

    if not result.get("is_confirmed_risk"):
        return AgentOutput(
            score=MentalHealthScore(
                stress_level=0, suicide_risk=0, burnout_score=0,
                depression_indicators=0, anxiety_markers=0, isolation_tendency=0,
            ),
            response="No significant mental health risk detected.",
        )

    scores_dict = result["hr_report"]["scores"]
    return AgentOutput(
        score=MentalHealthScore(**scores_dict),
        response=result["hr_report"]["response"],
    )


# Semaphore to limit concurrent LangGraph invocations (protects shared MCP client)
_BATCH_SEMAPHORE = asyncio.Semaphore(5)


async def _analyze_single_throttled(message: str, mcp_client: Client) -> AgentOutput:
    """Throttled wrapper around _analyze_single to limit concurrency."""
    async with _BATCH_SEMAPHORE:
        return await _analyze_single(message, mcp_client)


@app.post("/analyze/batch", response_model=BatchAgentOutput)
async def analyze_messages_batch(
    request: BatchAnalyzeRequest,
    mcp_client: Client = Depends(get_mcp_client),
):
    """Analyze multiple messages concurrently (max 5 at a time)."""
    logger.info(f"[BATCH] Received batch request: {len(request.messages)} messages")

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        tasks = [_analyze_single_throttled(msg, mcp_client) for msg in request.messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: List[AgentOutput] = []
        processed = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[BATCH] Message {i} failed: {result}")
                outputs.append(AgentOutput(
                    score=MentalHealthScore(
                        stress_level=0, suicide_risk=0, burnout_score=0,
                        depression_indicators=0, anxiety_markers=0, isolation_tendency=0,
                    ),
                    response=f"Analysis failed for this message: {str(result)}",
                ))
            else:
                outputs.append(result)
                processed += 1

        logger.info(f"[BATCH] Completed: {processed}/{len(request.messages)} messages successfully processed")
        return BatchAgentOutput(
            results=outputs,
            total=len(request.messages),
            processed=processed,
        )

    except Exception as e:
        logger.error(f"[BATCH] Batch analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check with dependencies."""
    return {
        "status": "healthy",
        "openai_api_configured": bool(os.getenv("OPENAI_API_KEY")),
        "prompt_service": "ready",
        "agent": "compiled"
    }
