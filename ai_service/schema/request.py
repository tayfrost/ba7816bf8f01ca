"""Request schemas for API endpoints."""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    """Request model for message analysis."""
    message: str
