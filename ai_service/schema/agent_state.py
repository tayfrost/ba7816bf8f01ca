"""Agent state schema for LangGraph workflow."""

from typing import TypedDict, Optional, Dict


class AgentState(TypedDict, total=False):
    """State dictionary for AI agent processing."""
    
    raw_message: str
    is_confirmed_risk: Optional[bool]
    retrieved_resources: Optional[list[dict]]
    hr_report: Optional[Dict[str, object]]     # Contains recommendations + detailed response
