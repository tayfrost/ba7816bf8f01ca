"""Output schema for mental health risk assessment responses."""

from typing import List
from pydantic import BaseModel, Field, field_validator


class MentalHealthScore(BaseModel):
    """Mental health dimension scores — field names match incident_scores DB columns."""

    neutral_score: int = Field(..., ge=0, le=100, description="Neutral / no-risk score (0-100)")
    humor_sarcasm_score: int = Field(..., ge=0, le=100, description="Humor or sarcasm present (0-100)")
    stress_score: int = Field(..., ge=0, le=100, description="Stress level (0-100)")
    burnout_score: int = Field(..., ge=0, le=100, description="Burnout indicators (0-100)")
    depression_score: int = Field(..., ge=0, le=100, description="Depression indicators (0-100)")
    harassment_score: int = Field(..., ge=0, le=100, description="Harassment / hostility (0-100)")
    suicidal_ideation_score: int = Field(..., ge=0, le=100, description="Suicidal ideation risk (0-100)")


class AgentOutput(BaseModel):
    """Output schema for AI agent response with validation."""
    
    score: MentalHealthScore = Field(..., description="Mental health risk scores across dimensions")
    response: str = Field(..., min_length=1, description="Generated text response from AI model")
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": {
                    "neutral_score": 10,
                    "humor_sarcasm_score": 5,
                    "stress_score": 65,
                    "burnout_score": 70,
                    "depression_score": 45,
                    "harassment_score": 20,
                    "suicidal_ideation_score": 10
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
