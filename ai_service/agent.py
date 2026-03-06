"""Mental health risk assessment agent with LangGraph workflow."""

import os
import json
import logging
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.prompt_service import PromptService
from services.mcp_service import load_mcp_tools
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore

load_dotenv()

app = FastAPI(title="SentinelAI Mental Health Assessment")

# Initialize services
prompt_service = PromptService()
llm = ChatOpenAI(
    model=os.getenv("MODEL", "gpt-5-nano"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=1
)


class AnalyzeRequest(BaseModel):
    """Request model for message analysis."""
    message: str


async def redactor(state: AgentState) -> AgentState:
    """Redact company-sensitive information while preserving employee mental health indicators."""
    logger.info("[NODE: redactor] Starting redaction")
    logger.debug(f"[NODE: redactor] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="redactor")
        logger.info("[NODE: redactor] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: redactor] Failed to load redactor prompt: {e}")
        raise
    
    human_prompt = f"""Original message: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"redacted_message": "message with company info redacted"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: redactor] Calling LLM for redaction")
    response = await llm.ainvoke(messages)
    result = json.loads(response.content)
    logger.info(f"[NODE: redactor] Redaction complete")
    
    state['raw_message'] = result['redacted_message']
    logger.info("[NODE: redactor] → Transition to assess_risk")
    return state


async def assess_risk(state: AgentState) -> AgentState:
    """Assess if message indicates mental health risk."""
    logger.info("[NODE: assess_risk] Starting risk assessment")
    logger.debug(f"[NODE: assess_risk] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="assess_risk")
        logger.info("[NODE: assess_risk] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: assess_risk] Failed to load prompt: {e}")
        raise
    
    human_prompt = f"""Analyze this message for mental health risk: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"is_risk": true/false, "reasoning": "brief explanation"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: assess_risk] Calling LLM for risk assessment")
    response = await llm.ainvoke(messages)
    result = json.loads(response.content)
    
    state['is_confirmed_risk'] = result['is_risk']
    logger.info(f"[NODE: assess_risk] Risk detected: {result['is_risk']}")
    logger.info(f"[NODE: assess_risk] Reasoning: {result.get('reasoning', 'N/A')}")
    
    next_node = "grade_message" if result['is_risk'] else "END"
    logger.info(f"[NODE: assess_risk] → Transition to {next_node}")
    return state


async def grade_message(state: AgentState) -> AgentState:
    """Grade message across mental health dimensions."""
    logger.info("[NODE: grade_message] Starting message grading")
    logger.debug(f"[NODE: grade_message] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="grade_message")
        logger.info("[NODE: grade_message] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: grade_message] Failed to load prompt: {e}")
        raise
    
    human_prompt = f"""Score this message on mental health dimensions (0-100): "{state['raw_message']}"

Respond with ONLY a JSON object:
{{
  "stress_level": 0-100,
  "suicide_risk": 0-100,
  "burnout_score": 0-100,
  "depression_indicators": 0-100,
  "anxiety_markers": 0-100,
  "isolation_tendency": 0-100
}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: grade_message] Calling LLM for scoring")
    response = await llm.ainvoke(messages)
    scores = json.loads(response.content)
    
    # Store scores in state for recommendations node
    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores
    
    logger.info(f"[NODE: grade_message] Scores: {scores}")
    logger.info("[NODE: grade_message] → Transition to generate_recommendations")
    return state


async def generate_recommendations(state: AgentState) -> AgentState:
    """Generate HR recommendations based on assessment with evidence-based advice from knowledge graph."""
    logger.info("[NODE: generate_recommendations] Starting recommendations generation")
    logger.debug(f"[NODE: generate_recommendations] Input state keys: {list(state.keys())}")
    
    try:
        system_prompt = prompt_service.load_prompt(subfolder="generate_recommendations")
        logger.info("[NODE: generate_recommendations] Prompt loaded successfully")
    except Exception as e:
        logger.error(f"[NODE: generate_recommendations] Failed to load prompt: {e}")
        raise
    
    scores = state['hr_report']['scores']
    raw_message = state['raw_message']
    
    # Load and bind MCP tools
    logger.info("[NODE: generate_recommendations] Loading MCP tools")
    kg_tools = await load_mcp_tools()
    logger.info(f"[NODE: generate_recommendations] Loaded {len(kg_tools)} MCP tools")
    
    llm_with_tools = llm.bind_tools(kg_tools) if kg_tools else llm
    
    human_prompt = f"""Based on message: "{raw_message}"
And scores: {json.dumps(scores)}

Use available MCP tools to gather evidence-based recommendations.
If crisis detected, prioritize crisis resources.
Generate HR recommendations and detailed analysis response.
Respond with JSON:
{{"recommendations": ["rec1", "rec2"], "response": "detailed analysis text"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    logger.info("[NODE: generate_recommendations] Calling LLM with bound MCP tools")
    response = await llm_with_tools.ainvoke(messages)
    result = json.loads(response.content)
    
    state['hr_report']['recommendations'] = result['recommendations']
    state['hr_report']['response'] = result['response']
    
    logger.info(f"[NODE: generate_recommendations] Generated {len(result['recommendations'])} recommendations")
    logger.info("[NODE: generate_recommendations] → Transition to END")
    return state


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
async def analyze_message(request: AnalyzeRequest):
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
        initial_state: AgentState = {"raw_message": request.message}
        logger.info("[API] Starting agent workflow")
        
        # Run agent workflow
        result = await agent.ainvoke(initial_state)
        logger.info("[API] Agent workflow completed")
        
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
