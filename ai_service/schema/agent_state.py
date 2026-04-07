"""Agent state schema for LangGraph workflow."""

from typing import Any, Dict, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """State dictionary for AI agent processing."""

    raw_message: str
    is_confirmed_risk: Optional[bool]
    retrieved_resources: Optional[list[dict]]
    hr_report: Optional[Dict[str, object]]     # Contains recommendations + detailed response
    # Metadata forwarded from webhooks
    user_id: Optional[str]
    company_id: Optional[int]
    source: Optional[str]
    sent_at: Optional[str]
    conversation_id: Optional[str]
    content_raw: Optional[Dict[str, Any]]
    filter_category: Optional[str]
    filter_severity: Optional[str]
