import os
from langchain_openai import ChatOpenAI


def get_llm(use_responses_api: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MODEL", "gpt-5-nano"),
        api_key=os.getenv("OPENAI_API_KEY"),
        use_responses_api=use_responses_api,
        temperature=1,
    )
