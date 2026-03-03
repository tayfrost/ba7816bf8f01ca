"""Mental health risk assessment agent with LangGraph workflow."""

import os
import json
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from services.prompt_service import PromptService
from services.mcp_service import call_mcp_tool
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore

load_dotenv()

app = FastAPI(title="SentinelAI Mental Health Assessment")

# Initialize services
prompt_service = PromptService()
llm = ChatOpenAI(
    model=os.getenv("MODEL", "gpt-5-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3
)


class AnalyzeRequest(BaseModel):
    """Request model for message analysis."""
    message: str


def redactor(state: AgentState) -> AgentState:
    """Redact company-sensitive information while preserving employee mental health indicators."""
    system_prompt = prompt_service.load_prompt(subfolder="redactor")
    human_prompt = f"""Original message: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"redacted_message": "message with company info redacted"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    response = llm.invoke(messages)
    result = json.loads(response.content)
    
    state['raw_message'] = result['redacted_message']
    return state


def assess_risk(state: AgentState) -> AgentState:
    """Assess if message indicates mental health risk."""
    system_prompt = prompt_service.load_prompt(subfolder="assess_risk")
    human_prompt = f"""Analyze this message for mental health risk: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"is_risk": true/false, "reasoning": "brief explanation"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    response = llm.invoke(messages)
    result = json.loads(response.content)
    
    state['is_confirmed_risk'] = result['is_risk']
    return state


def grade_message(state: AgentState) -> AgentState:
    """Grade message across mental health dimensions."""
    system_prompt = prompt_service.load_prompt(subfolder="grade_message")
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
    
    response = llm.invoke(messages)
    scores = json.loads(response.content)
    
    # Store scores in state for recommendations node
    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores
    
    return state


def generate_recommendations(state: AgentState) -> AgentState:
    """Generate HR recommendations based on assessment with evidence-based advice from knowledge graph."""
    system_prompt = prompt_service.load_prompt(subfolder="generate_recommendations")
    scores = state['hr_report']['scores']
    raw_message = state['raw_message']
    
    # Get evidence-based recommendations from knowledge graph
    kg_advice = None
    crisis_info = None
    try:
        # First, check for crisis indicators
        import asyncio
        crisis_result = asyncio.run(call_mcp_tool(
            "triage_crisis_risk",
            {"text": raw_message}
        ))
        crisis_data = json.loads(crisis_result) if isinstance(crisis_result, str) else crisis_result
        
        if crisis_data.get("crisis_detected"):
            crisis_info = crisis_data
        else:
            # Get personalized recommendations based on the message
            advice_result = asyncio.run(call_mcp_tool(
                "get_recommendation",
                {"diagnosis": raw_message, "max_results": 3}
            ))
            kg_advice = json.loads(advice_result) if isinstance(advice_result, str) else advice_result
    except Exception as e:
        print(f"Warning: Could not fetch knowledge graph recommendations: {e}")
    
    # Build context for LLM with KG recommendations
    kg_context = ""
    if crisis_info:
        kg_context = f"\n\nCRITICAL: Crisis detected. {crisis_info.get('agent_instructions')}\nCrisis Resources: {json.dumps(crisis_info.get('crisis_resources'))}"
    elif kg_advice and kg_advice.get('recommendations'):
        kg_context = "\n\nEvidence-based recommendations from peer-reviewed research:\n"
        for i, rec in enumerate(kg_advice['recommendations'][:3], 1):
            kg_context += f"{i}. {rec['advice']} (Confidence: {rec['confidence']}, Source: {rec['paper_title']}, DOI: {rec['doi']})\n"
        kg_context += f"\nDisclaimer: {kg_advice.get('disclaimer', '')}"
    
    human_prompt = f"""Based on message: "{raw_message}"
And scores: {json.dumps(scores)}
{kg_context}

Generate HR recommendations and detailed analysis response.
If crisis resources were provided, prioritize them in the response.
Respond with JSON:
{{"recommendations": ["rec1", "rec2"], "response": "detailed analysis text"}}"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    response = llm.invoke(messages)
    result = json.loads(response.content)
    
    state['hr_report']['recommendations'] = result['recommendations']
    state['hr_report']['response'] = result['response']
    
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
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    
    try:
        # Initialize state
        initial_state = AgentState(raw_message=request.message)
        
        # Run agent workflow
        result = agent.invoke(initial_state)
        
        # If no risk detected, return minimal response
        if not result.get('is_confirmed_risk'):
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
        scores_dict = result['hr_report']['scores']
        return AgentOutput(
            score=MentalHealthScore(**scores_dict),
            response=result['hr_report']['response']
        )
    
    except Exception as e:
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
