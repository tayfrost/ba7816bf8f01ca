"""Agent state schema for LangGraph workflow."""

from pydantic import BaseModel, Field
from typing import Optional


class AgentState(BaseModel):
    """State dictionary for AI agent processing."""
    
    raw_message: str = Field(..., description="Original message to analyze")
    is_confirmed_risk: Optional[bool] = Field(None, description="Whether mental health risk is confirmed")
    retrieved_resources: Optional[list[dict]] = Field(None, description="Retrieved resources for recommendations")
    hr_report: Optional[dict] = Field(None, description="Generated HR report with recommendations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "raw_message": "I've been feeling overwhelmed lately...",
                "is_confirmed_risk": True,
                "retrieved_resources": [{"type": "EAP", "contact": "1-800-XXX"}],
                "hr_report": {"risk_level": "moderate", "recommendations": []}
            }
        }
