"""Request schemas for API endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request model for single message analysis."""
    message: str
    user_id: Optional[str] = None
    company_id: Optional[int] = None
    source: Optional[str] = None
    sent_at: Optional[str] = None
    conversation_id: Optional[str] = None
    content_raw: Optional[Dict[str, Any]] = None
    filter_category: Optional[str] = None
    filter_severity: Optional[str] = None


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch message analysis."""
    messages: List[str] = Field(..., min_length=1, max_length=200)
