import os
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MODEL", "gemini-2.0-flash"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        temperature=1,
    )
