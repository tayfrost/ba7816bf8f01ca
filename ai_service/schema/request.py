"""Request schemas for API endpoints."""

from typing import List
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request model for single message analysis."""
    message: str


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch message analysis."""
    messages: List[str] = Field(..., min_length=1, max_length=50)
