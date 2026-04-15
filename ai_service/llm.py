import os
import logging
from langchain_openai import ChatOpenAI


logger = logging.getLogger(__name__)

def get_llm() -> ChatOpenAI:
    model = os.getenv("MODEL", "openrouter/free")
    logger.info("[LLM] Initializing JSON-mode client model=%s", model)
    return ChatOpenAI(
        model=model,
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
    model = os.getenv("MODEL", "openrouter/free")
    logger.info("[LLM] Initializing tool-call client model=%s", model)
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.1,
        model_kwargs={
            "extra_body": {
                "transforms": ["middle-out"]
            }
        }
    )
