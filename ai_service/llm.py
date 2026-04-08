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
