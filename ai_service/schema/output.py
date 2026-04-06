"""Output schema for mental health risk assessment responses."""

from typing import List
from pydantic import BaseModel, Field, field_validator


class MentalHealthScore(BaseModel):
    """Individual mental health dimension score."""
    
    stress_level: int = Field(..., ge=0, le=100, description="Stress level score (0-100)")
    suicide_risk: int = Field(..., ge=0, le=100, description="Suicide risk score (0-100)")
    burnout_score: int = Field(..., ge=0, le=100, description="Burnout score (0-100)")
    depression_indicators: int = Field(..., ge=0, le=100, description="Depression indicators score (0-100)")
    anxiety_markers: int = Field(..., ge=0, le=100, description="Anxiety markers score (0-100)")
    isolation_tendency: int = Field(..., ge=0, le=100, description="Isolation tendency score (0-100)")


class AgentOutput(BaseModel):
    """Output schema for AI agent response with validation."""
    
    score: MentalHealthScore = Field(..., description="Mental health risk scores across dimensions")
    response: str = Field(..., min_length=1, description="Generated text response from AI model")
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": {
                    "stress_level": 65,
                    "suicide_risk": 10,
                    "burnout_score": 70,
                    "depression_indicators": 45,
                    "anxiety_markers": 55,
                    "isolation_tendency": 30
                },
                "response": "Based on the analysis, moderate stress and burnout indicators detected..."
            }
        }
    
    @field_validator('response')
    @classmethod
    def response_not_empty(cls, v: str) -> str:
        """Ensure response is not just whitespace."""
        if not v.strip():
            raise ValueError("Response cannot be empty or whitespace only")
        return v


class BatchAgentOutput(BaseModel):
    """Output schema for batch analysis."""
    results: List[AgentOutput]
    total: int
    processed: int
