import os
from langchain_openai import ChatOpenAI

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MODEL", "openrouter/free"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1,
        # Force JSON mode and handle fallbacks
        model_kwargs={
            "response_format": {"type": "json_object"},
            "extra_body": {
                "transforms": ["middle-out"]
            }
        }
    )


def get_llm_for_tools() -> ChatOpenAI:
    """LLM variant for tool-calling nodes. No response_format — combining
    JSON mode with non-strict MCP tool schemas breaks on some OpenRouter models."""
    return ChatOpenAI(
        model=os.getenv("MODEL", "openrouter/free"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1,
        model_kwargs={
            "extra_body": {
                "transforms": ["middle-out"]
            }
        }
    )
