"""Mental health risk assessment agent with LangGraph workflow."""

import os
import logging
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.prompt_service import PromptService
from services.mcp_service import get_mcp_client
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore
from schema.request import AnalyzeRequest

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
async def analyze_message(request: AnalyzeRequest, mcp_client=Depends(get_mcp_client)):
    """Analyze message for mental health risks."""
    logger.info("="*80)
    logger.info(f"[API] New analyze request received")
    logger.info(f"[API] Message length: {len(request.message)} chars")
    logger.info("="*80)
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("[API] OPENAI_API_KEY not configured")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    try:
        # Initialize state
        initial_state: AgentState = {"raw_message": request.message, "mcp_client": mcp_client}
        logger.info("[API] Starting agent workflow")
        
        # Run agent workflow
        result = await agent.ainvoke(initial_state)
        logger.info("[API] Agent workflow completed")
        
        # Remove non-serializable mcp_client from result
        result.pop('mcp_client', None)
        
        # If no risk detected, return minimal response
        if not result.get('is_confirmed_risk'):
            logger.info("[API] No risk detected, returning minimal response")
            return AgentOutput(
                score=MentalHealthScore(
                    stress_level=0,
                    suicide_risk=0,
                    burnout_score=0,
                    depression_indicators=0,
                    anxiety_markers=0,
                    isolation_tendency=0
                ),
                response="No significant mental health risk detected."
            )
            
        logger.info(f"[API] Final response: {result}")
        
        # Return full assessment
        logger.info("[API] Risk confirmed, returning full assessment")
        scores_dict = result['hr_report']['scores']
        logger.info(f"[API] Final scores: {scores_dict}")
        return AgentOutput(
            score=MentalHealthScore(**scores_dict),
            response=result['hr_report']['response']
        )
    
    except Exception as e:
        logger.error(f"[API] Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check with dependencies."""
    return {
        "status": "healthy",
        "openai_api_configured": bool(os.getenv("OPENAI_API_KEY")),
        "prompt_service": "ready",
        "agent": "compiled"
    }
