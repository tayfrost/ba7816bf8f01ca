"""Mental health risk assessment agent with LangGraph workflow."""

import os
import json
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from services.prompt_service import PromptService
from schema.agent_state import AgentState
from schema.output import AgentOutput, MentalHealthScore

load_dotenv()

app = FastAPI(title="SentinelAI Mental Health Assessment")

# Initialize services
prompt_service = PromptService()
llm = ChatMistralAI(
    model="mistral-large-latest",
    api_key=os.getenv("MISTRAL_API_KEY"),
    temperature=0.3
)


class AnalyzeRequest(BaseModel):
    """Request model for message analysis."""
    message: str


def assess_risk(state: AgentState) -> AgentState:
    """Assess if message indicates mental health risk."""
    system_prompt = prompt_service.load_prompt()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Analyze this message for mental health risk: "{state['raw_message']}"

Respond with ONLY a JSON object:
{{"is_risk": true/false, "reasoning": "brief explanation"}}""")
    ]
    
    response = llm.invoke(messages)
    result = json.loads(response.content)
    
    state['is_confirmed_risk'] = result['is_risk']
    return state


def grade_message(state: AgentState) -> AgentState:
    """Grade message across mental health dimensions."""
    system_prompt = prompt_service.load_prompt()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Score this message on mental health dimensions (0-100): "{state['raw_message']}"

Respond with ONLY a JSON object:
{{
  "stress_level": 0-100,
  "suicide_risk": 0-100,
  "burnout_score": 0-100,
  "depression_indicators": 0-100,
  "anxiety_markers": 0-100,
  "isolation_tendency": 0-100
}}""")
    ]
    
    response = llm.invoke(messages)
    scores = json.loads(response.content)
    
    # Store scores in state for recommendations node
    if state.get('hr_report') is None:
        state['hr_report'] = {}
    state['hr_report']['scores'] = scores
    
    return state


def generate_recommendations(state: AgentState) -> AgentState:
    """Generate HR recommendations based on assessment."""
    system_prompt = prompt_service.load_prompt()
    scores = state['hr_report']['scores']
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Based on message: "{state['raw_message']}"
And scores: {json.dumps(scores)}

Generate HR recommendations and detailed analysis response.
Respond with JSON:
{{"recommendations": ["rec1", "rec2"], "response": "detailed analysis text"}}""")
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

workflow.add_node("assess_risk", assess_risk)
workflow.add_node("grade_message", grade_message)
workflow.add_node("generate_recommendations", generate_recommendations)

workflow.set_entry_point("assess_risk")
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
    if not os.getenv("MISTRAL_API_KEY"):
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY not configured")
    
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
        "mistral_api_configured": bool(os.getenv("MISTRAL_API_KEY")),
        "prompt_service": "ready",
        "agent": "compiled"
    }
